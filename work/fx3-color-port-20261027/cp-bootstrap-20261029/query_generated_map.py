#!/usr/bin/env python3
"""Original pointer-query on explicitly pre-barrier software-table snapshot only."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from bootstrap_guest import Guest,SOURCE,PIN,ROOT,STACK
HERE=Path(__file__).resolve().parent
def main():
    out=HERE/'generated-map-query.json';assert not out.exists();raw=SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
    g=Guest(raw,0);boot=g.call(0x1083a4,stops={0x108728:'before_CPU_setup_call'});assert boot['boundary']['PC']=='0x108728'
    init=g.call(0x553d48,[ROOT]);assert init['boundary']['PC']=='0x5541e4'
    results=[]
    for address in [0x09a08e00,0x128000,0x0]:
        output=STACK+0x8000;g.u.mem_write(output,b'\xa7'*4)
        query=g.call(0x54bbd0,[address,output]);attrs=g.words(output,1)[0]
        validate=g.call(0x53894c,[address]);results.append(dict(address=hex(address),original_attribute_query=query,
            output_word=hex(attrs),original_pointer_check=validate,
            scope='A software-table snapshot before the first MMU-init barrier; not fully initialized/live CPU mapping or a readable physical buffer.'))
    record=dict(CP_sha256=PIN,declared_optional_hardware_flag=0,bootstrap_body=boot,partial_MMU_init=init,cases=results,
        scope='All table and attribute words are produced/read by original instructions, without a fabricated MMU/attribute reply. The actual full startup poll, hardware flag, CPU setup, barrier/TLB state and completion of MMU init are not verified. No DmmCfg bytes loaded at0x09a08e00, buffer allocation, physical pixels, native Sony execution or device action.')
    out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps([dict(address=r['address'],query_stop=r['original_attribute_query']['boundary'],attributes=r['output_word'],pointer_check=r['original_pointer_check']['registers'][0],pointer_stop=r['original_pointer_check']['boundary']) for r in results]))
if __name__=='__main__':main()
