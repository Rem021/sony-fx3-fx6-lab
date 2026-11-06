#!/usr/bin/env python3
"""Additional new-object guard checks using already produced native inputs."""
from pathlib import Path
import datetime,hashlib,json,struct,sys,traceback
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import audio_proxy as t
f=t.front
def sha(b):return hashlib.sha256(b).hexdigest()
def one(source,kind):
    m=f.Guest(source['seed'])
    try:
        m.uc.mem_write(f.CODE,t.IMAGE);m.images=[(a,d) for a,d in m.images if a!=f.CODE]+[(f.CODE,t.IMAGE)]
        m.allowed=[(a,z) for a,z in m.allowed if not(f.CODE<=a<f.CODE+0x2000)]+[(f.CODE,f.CODE+t.SIZE),(f.CODE+0x1000,f.CODE+0x1030)]
        f.fixture(m,source['seed'],0x2e6f9b0)
        p=bytearray.fromhex(source['native_param_hex']);m.uc.mem_write(f.SRC,bytes(p))
        gp=f.GATE;src=f.SRC;dst=f.DST;site=0x2e6f9b0;epoch=f.EPOCH
        def gate(at,value):m.uc.mem_write(f.GATE+at,struct.pack('<Q',value))
        expected=5
        if kind=='magic':gate(0,f.MAGIC^1);expected=1
        elif kind=='gate_address':gp+=8;expected=1
        elif kind=='closed':gate(8,0);expected=2
        elif kind=='epoch':epoch+=1;expected=3
        elif kind=='site':site+=4;expected=4
        elif kind=='overlap':dst=src+8;gate(56,dst)
        elif kind=='control_destination':dst=f.GATE;gate(56,dst)
        elif kind=='source_outside':src=0xfffffffffffffff0;gate(48,src)
        elif kind.startswith('aux_'):
            ptr={'aux_overlap':dst,'aux_gate':f.GATE,'aux_outside':0xfffffffffffffff0}[kind]
            struct.pack_into('<I',p,0x118,48);struct.pack_into('<Q',p,0x120,ptr);m.uc.mem_write(f.SRC,bytes(p))
        e=m.phase('new compiled frontend original-gate regression '+kind,t.ENTRY,abi=True,
            sp=t.SP,x30=t.pp.STOP,x0=gp,x1=src,x2=dst,x3=site,x4=epoch)
        assert e['return_u32_if_returned']==expected
        assert bytes(m.uc.mem_read(f.SRC,0x1c0))==bytes(p)
        return {'seed':source['seed'],'kind':kind,'expected_status':expected,'events':[e],
            'actual_gate_epoch_or_camera_permission_proven':False}
    finally:m.close()
def run():
    t.im.volume();prior=STAGE/'run-original-helpers-and-admission-20261027'
    j=json.loads((prior/'audio-proxy-results.json').read_text());assert j['status']=='PASS_NATIVE_AUDIO_PROXY_PRODUCTION_AND_GUEST_ONLY_ADMISSION_REFINEMENT'
    assert (prior/'executed-source.py').read_bytes()==(STAGE/'audio_proxy.py').read_bytes()
    out=STAGE/'run-new-object-guard-regression-20261027';out.mkdir();(out/'executed-source.py').write_bytes(Path(__file__).read_bytes())
    result={'source_sha256':sha(Path(__file__).read_bytes()),'reused_native_inputs_sha256':sha((prior/'audio-proxy-results.json').read_bytes()),
        'object_sha256':sha((STAGE/'scoped_frontend.a64.o').read_bytes()),'cases':[],'passing_result':False}
    try:
        for source in [x for x in j['caller_cases'] if x['label']=='HEVC16']:
            for kind in ('magic','gate_address','closed','epoch','site','overlap','control_destination','source_outside','aux_overlap','aux_gate','aux_outside'):
                result['cases'].append(one(source,kind))
        result['passing_result']=True;result['bounded_phases']=len(result['cases']);result['created_utc']=datetime.datetime.now(datetime.timezone.utc).isoformat()
        (out/'guard-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
        print(json.dumps({'bounded_phases':result['bounded_phases'],'passing_result':True,'original_matrix_not_rerun':True}))
    except Exception:
        result['error']=traceback.format_exc();(out/'attempt-failure.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');raise
if __name__=='__main__':run()
