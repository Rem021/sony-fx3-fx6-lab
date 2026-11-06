#!/usr/bin/env python3
"""Decode one bounded FX3MS1 maps snapshot; console noise is not data."""
import argparse,base64,hashlib,json,re,sys

class ProtocolError(ValueError):
    pass

def fnv1a(b):
    h=1469598103934665603
    for x in b:h=(h^x)*1099511628211&0xffffffffffffffff
    return h

def kv(parts):
    d={}
    for p in parts:
        if '=' not in p:raise ProtocolError('field without =: '+p[:40])
        k,v=p.split('=',1);d[k]=v
    return d

def decode(text):
    frames=[];cur=None;noise=[]
    for raw in text.splitlines():
        if not raw.startswith('FX3MS1 '):
            noise.append(raw)
            continue
        parts=raw.split()
        if len(parts)<2 or parts[0]!='FX3MS1':raise ProtocolError('bad prefix')
        typ=parts[1]
        if typ=='BEGIN':
            if cur is not None:raise ProtocolError('nested BEGIN before END')
            d=kv(parts[2:]);
            for k in ('pid','starttime','seq','cap','single_read'):
                if k not in d:raise ProtocolError('BEGIN missing '+k)
            if d['single_read']!='1':raise ProtocolError('single_read required')
            cur={'begin':d,'chunks':[],'chunk_seq':-1,'ended':None}
        elif typ=='DATA':
            if cur is None:raise ProtocolError('DATA without BEGIN')
            if len(parts)<4:raise ProtocolError('DATA malformed')
            try:i=int(parts[2])
            except ValueError:raise ProtocolError('DATA seq')
            if i!=cur['chunk_seq']+1:raise ProtocolError('DATA out of order/duplicate')
            try:b=base64.b64decode(parts[3],validate=True)
            except Exception as e:raise ProtocolError('DATA base64: '+repr(e))
            cur['chunks'].append(b);cur['chunk_seq']=i
        elif typ=='END':
            if cur is None:raise ProtocolError('END without BEGIN')
            d=kv(parts[2:]);cur['ended']=d
            for k in ('pid','starttime','seq','bytes','lines','digest','line_terminated','complete','snapshot_atomic'):
                if k not in d:raise ProtocolError('END missing '+k)
            blob=b''.join(cur['chunks']);b0=cur['begin']
            for k in ('pid','starttime','seq'):
                if d[k]!=b0[k]:raise ProtocolError('identity change '+k)
            if d['line_terminated']!='1':raise ProtocolError('unterminated maps')
            if d['complete']!='1':raise ProtocolError('incomplete flag')
            if d['snapshot_atomic']!='0':raise ProtocolError('atomic snapshot claim unsupported')
            if int(d['bytes'])!=len(blob):raise ProtocolError('length mismatch')
            if int(d['lines'])!=blob.count(b'\n'):raise ProtocolError('line count mismatch')
            if d['digest']!='fnv1a64:%016x'%fnv1a(blob):raise ProtocolError('digest mismatch')
            frames.append({'begin':b0,'end':d,'blob':blob});cur=None
        elif typ=='ERROR':
            raise ProtocolError('collector ERROR: '+raw[:160])
        else:raise ProtocolError('unknown frame '+typ)
    if cur is not None:raise ProtocolError('missing END')
    if len(frames)!=1:raise ProtocolError('expected exactly one frame, got %d'%len(frames))
    f=frames[0];b=f['blob']
    if len(b)>int(f['begin']['cap']):raise ProtocolError('cap exceeded')
    return {'status':'ACCEPTED_BOUNDED_SINGLE_READ_NOT_ATOMIC','pid':int(f['begin']['pid']),'starttime':int(f['begin']['starttime']),'seq':int(f['begin']['seq']),'cap':int(f['begin']['cap']),'bytes':len(b),'lines':b.count(b'\n'),'line_terminated':True,'digest':'fnv1a64:%016x'%fnv1a(b),'snapshot_atomic':False,'maps_sha256':hashlib.sha256(b).hexdigest(),'console_noise_lines':len(noise),'maps_text':b.decode('utf-8','replace'),'note':'bounded single read; not an atomic kernel snapshot and not a boot/menu proof'}

def main(argv=None):
    ap=argparse.ArgumentParser();ap.add_argument('--input',required=True);ap.add_argument('--output',required=True);a=ap.parse_args(argv)
    try:
        out=decode(open(a.input,encoding='utf-8',errors='replace').read());rc=0
    except ProtocolError as e:
        out={'status':'REJECTED','error':str(e)};rc=1
    open(a.output,'w').write(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'pid':out.get('pid'),'bytes':out.get('bytes'),'noise':out.get('console_noise_lines'),'error':out.get('error'),'output':a.output}));return rc
if __name__=='__main__':sys.exit(main())
