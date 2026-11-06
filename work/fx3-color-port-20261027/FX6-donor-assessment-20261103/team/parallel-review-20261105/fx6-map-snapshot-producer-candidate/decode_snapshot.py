#!/usr/bin/env python3
"""Strict decoder for bounded FX3MS1 map snapshots (offline only).

One read + one EOF probe.  `snapshot_atomic=0` always: this is a bounded
stream capture, not an atomic kernel maps snapshot.  Console noise is ignored
only when it does not start with the FX3MS1 prefix.
"""
import argparse,base64,hashlib,json,re,sys
FNV_OFFSET=14695981039346656037
FNV_PRIME=1099511628211
MAX_CAP=1048576
HEX64=re.compile(r'^[0-9a-f]{16}$')
class ProtocolError(ValueError):pass

def fnv1a(b):
    h=FNV_OFFSET
    for x in b:h=(h^x)*FNV_PRIME&0xffffffffffffffff
    return h

def _num(v,name,lo=None,hi=None):
    if len(v)>20:raise ProtocolError('%s too long'%name)
    try:n=int(v,10)
    except (TypeError,ValueError):raise ProtocolError('bad numeric %s=%r'%(name,v[:40]))
    if lo is not None and n<lo:raise ProtocolError('%s out of range'%name)
    if hi is not None and n>hi:raise ProtocolError('%s out of range'%name)
    return n

def _kv(parts,required):
    if len(parts)!=len(required) or len({p.split('=',1)[0] for p in parts if '=' in p})!=len(parts):raise ProtocolError('field count/duplicate')
    d={}
    for p in parts:
        if '=' not in p:raise ProtocolError('field without =')
        k,v=p.split('=',1)
        if not k or not v or k in d:raise ProtocolError('bad/duplicate field')
        d[k]=v
    if set(d)!=set(required):raise ProtocolError('unexpected fields')
    return d

MAX_FRAMES=16
MAX_LINES=200000
MAX_LINE=65536
MAX_NOISE=20000
MAX_CHUNK_B64=4096

def _parse_frame(lines):
    if len(lines)>MAX_LINES:raise ProtocolError('too many input lines')
    frame_count=0;latest=None;first_id=None;first_seq=None;noise_count=0;cur=None
    for raw in lines:
        if len(raw)>MAX_LINE:raise ProtocolError('line too long')
        if not raw.startswith('FX3MS1 '):
            noise_count+=1
            if noise_count>MAX_NOISE:raise ProtocolError('too much console noise')
            continue
        parts=raw.split()
        if len(parts)<2:raise ProtocolError('bad FX3MS1 line')
        typ=parts[1]
        if typ=='BEGIN':
            if cur is not None:raise ProtocolError('BEGIN before prior END')
            d=_kv(parts[2:],('pid','starttime','seq','cap','data_reads','eof_probe','data_attempts','eof_attempts','capture'))
            if d['capture']!='bounded_single_read':raise ProtocolError('bad capture')
            pid=_num(d['pid'],'pid',1,2147483647);st=_num(d['starttime'],'starttime',0);seq=_num(d['seq'],'seq',0);cap=_num(d['cap'],'cap',1,MAX_CAP)
            if _num(d['data_reads'],'data_reads')!=1 or _num(d['eof_probe'],'eof_probe')!=1:raise ProtocolError('read/probe not one')
            if not 1<=_num(d['data_attempts'],'data_attempts',1,3)<=3 or not 1<=_num(d['eof_attempts'],'eof_attempts',1,3)<=3:raise ProtocolError('attempts out of range')
            if first_id is not None and (pid,st)!=first_id:raise ProtocolError('mixed PID/starttime frames')
            if first_seq is not None and seq<=first_seq:raise ProtocolError('duplicate/out-of-order sequence')
            cur={'begin':d,'pid':pid,'starttime':st,'seq':seq,'cap':cap,'blob':bytearray(),'next':0,'data_attempts':_num(d['data_attempts'],'data_attempts',1,3),'eof_attempts':_num(d['eof_attempts'],'eof_attempts',1,3)}
        elif typ=='DATA':
            if cur is None:raise ProtocolError('DATA without BEGIN')
            if len(parts)!=7:raise ProtocolError('DATA token count')
            i=_num(parts[2],'DATA index',0,1000000)
            if i!=cur['next']:raise ProtocolError('DATA out of order/duplicate')
            dpid=_num(parts[3],'DATA pid',1,2147483647);dst=_num(parts[4],'DATA starttime',0);dseq=_num(parts[5],'DATA seq',0)
            if (dpid,dst,dseq)!=(cur['pid'],cur['starttime'],cur['seq']):raise ProtocolError('DATA identity mismatch')
            enc=parts[6]
            if not enc or len(enc)%4 or len(enc)>MAX_CHUNK_B64:raise ProtocolError('DATA base64 size')
            try:rawb=base64.b64decode(enc,validate=True)
            except Exception:raise ProtocolError('DATA base64')
            if not rawb:raise ProtocolError('empty DATA chunk')
            if len(cur['blob'])+len(rawb)>=cur['cap']:raise ProtocolError('data reaches/exceeds cap')
            cur['blob'].extend(rawb);cur['next']+=1
        elif typ=='END':
            if cur is None:raise ProtocolError('END without BEGIN')
            d=_kv(parts[2:],('pid','starttime','seq','bytes','lines','digest','line_terminated','complete','snapshot_atomic','data_reads','eof_probe','eof_observed','data_attempts','eof_attempts'))
            if (d['pid'],d['starttime'],d['seq'])!=(str(cur['pid']),str(cur['starttime']),str(cur['seq'])):raise ProtocolError('identity change')
            if d['data_reads']!='1' or d['eof_probe']!='1' or d['eof_observed']!='1':raise ProtocolError('read/probe evidence missing')
            if _num(d['data_attempts'],'data_attempts',1,3)!=cur['data_attempts'] or _num(d['eof_attempts'],'eof_attempts',1,3)!=cur['eof_attempts']:raise ProtocolError('attempts change')
            if d['line_terminated']!='1':raise ProtocolError('unterminated flag')
            if d['complete']!='1':raise ProtocolError('incomplete flag')
            if d['snapshot_atomic']!='0':raise ProtocolError('atomic snapshot claim unsupported')
            blob=bytes(cur['blob'])
            if not blob:raise ProtocolError('empty payload')
            if len(blob)>=cur['cap'] or len(blob)>cur['cap']:raise ProtocolError('data reaches/exceeds cap')
            if len(blob)!=_num(d['bytes'],'bytes'):raise ProtocolError('length mismatch')
            if blob[-1:]!=b'\n':raise ProtocolError('payload final byte not newline')
            actual_lines=blob.count(b'\n')
            if actual_lines<=0:raise ProtocolError('zero lines')
            if actual_lines!=_num(d['lines'],'lines'):raise ProtocolError('line count mismatch')
            if d['digest']!='fnv1a64:%016x'%fnv1a(blob):raise ProtocolError('digest mismatch')
            # keep only the latest valid frame; prior blobs are dropped
            if frame_count>=MAX_FRAMES:raise ProtocolError('too many frames')
            if first_id is None:first_id=(cur['pid'],cur['starttime'])
            first_seq=cur['seq'];latest=(cur,d);frame_count+=1;cur=None
        elif typ=='ERROR':raise ProtocolError('collector ERROR: '+raw[:160])
        else:raise ProtocolError('unknown frame '+typ)
    if cur is not None:raise ProtocolError('missing END')
    if latest is None:raise ProtocolError('no complete frame')
    f,end=latest;b=bytes(f['blob'])
    meta={'pid':f['pid'],'starttime':f['starttime'],'seq':f['seq'],'cap':f['cap'],'bytes':len(b),'lines':b.count(b'\n'),'line_terminated':True,'digest':'fnv1a64:%016x'%fnv1a(b),'snapshot_atomic':False,'data_reads':1,'eof_probe':1,'eof_observed':1,'data_attempts':f['data_attempts'],'eof_attempts':f['eof_attempts'],'maps_sha256':hashlib.sha256(b).hexdigest(),'console_noise_lines':noise_count,'frame_count':frame_count,'selected_seq':f['seq'],'maps_text':b.decode('utf-8','replace'),'note':'one bounded read + EOF probe; not an atomic kernel snapshot and not boot/menu proof'}
    return {'status':'ACCEPTED_BOUNDED_SINGLE_READ_NOT_ATOMIC',**meta}

def decode(text):return _parse_frame(text.splitlines())

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);a=ap.parse_args(argv)
    try:
        out=decode(open(a.input,encoding='utf-8',errors='replace').read());rc=0
    except ProtocolError as e:
        out={'status':'REJECTED','error':str(e)};rc=1
    open(a.output,'w').write(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'pid':out.get('pid'),'bytes':out.get('bytes'),'frames':out.get('frame_count'),'noise':out.get('console_noise_lines'),'error':out.get('error'),'output':a.output}));return rc
if __name__=='__main__':sys.exit(main())
