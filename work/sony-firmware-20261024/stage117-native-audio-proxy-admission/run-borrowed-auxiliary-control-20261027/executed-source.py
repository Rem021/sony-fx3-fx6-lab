#!/usr/bin/env python3
"""Keep valid borrowed auxiliary data covered after admission refinement."""
from pathlib import Path
import copy,hashlib,json,struct,sys
STAGE=Path(__file__).resolve().parent;sys.path.insert(0,str(STAGE));import audio_proxy as t
def run():
    t.im.volume();p=STAGE/'run-original-helpers-and-admission-20261027/audio-proxy-results.json'
    j=json.loads(p.read_text());out=STAGE/'run-borrowed-auxiliary-control-20261027';out.mkdir()
    (out/'executed-source.py').write_bytes(Path(__file__).read_bytes());cases=[]
    for native in [x for x in j['caller_cases'] if x['label']=='HEVC16']:
        source=copy.deepcopy(native);b=bytearray.fromhex(source['native_param_hex'])
        struct.pack_into('<I',b,0x118,48);struct.pack_into('<Q',b,0x120,t.front.AUX)
        source['native_param_hex']=b.hex();r=t.admit(source)
        assert r['admitted_in_guest'];r['explicit_borrowed_auxiliary_fixture']={'bytes':48,'pointer':hex(t.front.AUX),
            'not_generated_by_audio_proxy_helper':True,'full_setter_and_owned_snapshot_not_run':True};cases.append(r)
    result={'passing_result':True,'cases':cases,'bounded_phases':2,
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'reused_native_inputs_sha256':hashlib.sha256(p.read_bytes()).hexdigest(),
        'object_sha256':hashlib.sha256((STAGE/'scoped_frontend.a64.o').read_bytes()).hexdigest()}
    (out/'aux-borrow-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps({'passing_result':True,'bounded_phases':2,'matrix_not_rerun':True}))
if __name__=='__main__':run()
