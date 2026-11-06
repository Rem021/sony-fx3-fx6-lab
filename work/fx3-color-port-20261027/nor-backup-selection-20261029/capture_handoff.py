#!/usr/bin/env python3
"""Record original Cetus handoff checks without providing completion markers."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from check_file_open import FileGuest,inputs,old
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    out=HERE/'handoff-boundaries.json';assert not out.exists()
    raw,record,source,bank=inputs();context=old.OUT+0x3000;cases=[]
    for name,entry,address in [('CP_APP_B',0xfe052e74,0x800107f20),('CP_ESCAPE',0xfe052de0,0x800107f30)]:
        g=FileGuest(raw,record)
        if name=='CP_ESCAPE':g.u.mem_write(context+0x1b4,(2).to_bytes(4,'little'))
        result=g.call(entry,[context])
        assert result['boundary']['reason']=='unmapped_external_state' and result['boundary']['address']==hex(address)
        cases.append(dict(name=name,result=result,completion_marker_supplied=False,
            explicit_context_input='For CP_ESCAPE only, context+0x1b4=2 selects the original marker-check branch. No marker or transfer completion is supplied.'))
    cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);fragments=[]
    for lo,hi in [(0xfe052de0,0xfe052e74),(0xfe052e74,0xfe052ee8),(0xfe052ee8,0xfe052fc0)]:
        data=raw[lo-old.BASE:hi-old.BASE];f=HERE/'source-fragments'/f'{lo:08x}-{hi:08x}.txt';assert not f.exists()
        f.write_text('\n'.join(f'{x.address:08x} {x.bytes.hex()} {x.mnemonic:8} {x.op_str}' for x in cs.disasm(data,lo))+'\n')
        fragments.append(dict(VA=hex(lo),end_exclusive=hex(hi),bytes=len(data),original_bytes_sha256=sha(data),listing=str(f.relative_to(HERE))))
    logs=[]
    for address in [0xfe05e4cc,0xfe05e4f4,0xfe05e539,0xfe05e561,0xfe05e4b5]:
        at=address-old.BASE;end=raw.index(b'\0',at);logs.append(dict(VA=hex(address),text=raw[at:end].decode()))
    result=dict(NOR_sha256=old.PIN,source_fragments=fragments,original_log_strings=logs,cases=cases,
        source_contract=dict(CP_APP_B_marker_address='0x800107f20',CP_APP_B_marker_value='0x454e524b',
            CP_APP_B_following_pointer_offset=8,CP_ESCAPE_marker_address='0x800107f30',CP_ESCAPE_marker_value='0x50435345'),
        scope='Original logs and marker-consumer prefixes identify a separate handoff avenue. They do not identify the sender, prove any marker present, show DmmCfg transfer, establish firmware admission or constitute actual camera/USB operation.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=[dict(name=x['name'],boundary=x['result']['boundary']) for x in cases],logs=logs)))
if __name__=='__main__':main()
