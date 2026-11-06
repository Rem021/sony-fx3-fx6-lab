#!/usr/bin/env python3
"""Original memcfg parsing and explicitly CPU-disabled software attribute projection."""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from region_list_guest import RegionGuest,old,snapshot
HERE=Path(__file__).resolve().parent
TOMCO=HERE.parent/'dmm-backup-20261029/tomco.txt'
class AttrGuest(RegionGuest):
    def code(self,u,pc,size,user):
        if pc==0x555374:
            assert bytes(u.mem_read(pc,4))==bytes.fromhex('4ff07ff5')
            self.allowed_barriers.append(dict(PC=hex(pc),instruction='dsb sy',
                scope='Original DSB executed only in Unicorn; physical synchronization is not modeled.'))
            self.instructions+=1
            return
        super().code(u,pc,size,user)
def prepare(raw):
    g=AttrGuest(raw)
    assert g.call(0x1083a4,stops={0x108728:'before_CPU_setup_call'})['boundary']['PC']=='0x108728'
    assert g.call(0x553d48,[old.ROOT])['boundary']['reason']=='returned'
    assert g.call(0x54ad3c,stops={0x54ae54:'before_original_mutex_initializer_call'})['boundary']['PC']=='0x54ae54'
    assert g.call(0x54ae5c,stops={0x54b3b4:'before_following_cache_helper'})['boundary']['PC']=='0x54b3b4'
    return g
def main():
    out=HERE/'tomco-request-results.json';assert not out.exists()
    raw=old.SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==old.PIN
    tomco=TOMCO.read_bytes()
    seal=json.loads((TOMCO.parent/'final-receipt.json').read_text())
    pin=[x for x in seal['files'] if x['path']=='tomco.txt'];assert len(pin)==1
    assert len(tomco)==pin[0]['bytes'] and hashlib.sha256(tomco).hexdigest()==pin[0]['sha256']
    lines=[x for x in tomco.splitlines() if x==b'memcfg=0x7000000@0x09000000:uc'];assert len(lines)==1
    value=lines[0].split(b'=',1)[1]
    g=prepare(raw)
    data=old.STACK+0x7000;g.u.mem_write(data,value+b'\0')
    g.u.reg_write(old.R.UC_ARM_REG_R4,data)
    parsed=g.call(0x546b2c,stops={0x546c9c:'before_original_SetAttr_call'})
    assert parsed['boundary']['PC']=='0x546c9c'
    args=[int(x,16) for x in parsed['registers'][:3]]
    assert args==[0x09000000,0x07000000,0x20],args
    strict=g.call(0x54b4b8,args)
    # No cache geometry/CPU registers are filled to make this normal path pass.
    assert strict['boundary']['reason']!='returned'
    projected=prepare(raw)
    projection_args=[args[0],args[1],args[2]|0x20000000]
    projection=projected.call(0x54b4b8,projection_args)
    after=snapshot(projected,'software_only_CPU_disabled_attribute_projection')
    result=dict(CP_sha256=old.PIN,TOMCO_source=str(TOMCO),TOMCO_sha256=pin[0]['sha256'],
        original_line=lines[0].decode(),original_value_fragment=parsed,observed_original_SetAttr_arguments=list(map(hex,args)),
        strict_original_SetAttr=strict,software_projection_arguments=list(map(hex,projection_args)),
        software_projection=projection,snapshot=after,
        modeled_DSB_events=projected.allowed_barriers,
        scope='Only the original value-parsing fragment is used, not full TOMCO boot loading. The strict original SetAttr path does not receive fabricated cache/CPU state. A separate projection explicitly adds the original CPU-maintenance-disable argument bit0x20000000; this is not the TOMCO call or actual cache/TLB synchronization. It only tests original RAM table effects with unchanged firmware instructions. No candidate DmmCfg bytes, physical buffer, RAW pixels or device action.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(parsed=parsed['boundary'],original_args=list(map(hex,args)),strict=strict['boundary'],
        projection_args=list(map(hex,projection_args)),projection=projection['boundary'],
        queries=[dict(address=x['address'],attributes=x['attributes'],query_R0=x['attribute_call']['registers'][0],
        pointer_R0=x['pointer_call']['registers'][0]) for x in after['cases']])) )
if __name__=='__main__':main()
