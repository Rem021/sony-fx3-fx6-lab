#!/usr/bin/env python3
"""Original ART descriptor dispatch, with semantic setter hooks (not pixels)."""
from pathlib import Path
import hashlib,json,struct
from unicorn import arm64_const as arm
from art_matrix_guest import Guest,HERE
from macho_static import MachO


class DispatchGuest(Guest):
    def __init__(self,m):
        self.recorded=[];self.pairs=[]
        super().__init__(m,[0x1b228])

    def hook(self,uc,pc,size,user):
        if pc in [0x1b658,0x1b7e8,0x1bb80,0x1bd54]:
            self.steps+=1
            args=[uc.reg_read(getattr(arm,'UC_ARM64_REG_X'+str(i))) for i in range(8)]
            if pc==0x1b658:
                # Only record the two-int descriptor insertion; this dispatch
                # never reads the resulting controller vector in this call.
                b=self.uq(args[1]);e=self.uq(args[1]+8);assert e-b==8
                self.pairs.append(list(struct.unpack('<ii',uc.mem_read(b,8))))
            else:
                self.recorded.append(dict(kind={0x1b7e8:'3D',0x1bb80:'LMX',0x1bd54:'1D'}[pc],
                    source_offset=args[1]-self.record,
                    parameter_data_offset=args[2]-self.output,
                    parameter_info_offset=args[3]-self.output,
                    integer_args=args[4:]))
            uc.reg_write(arm.UC_ARM64_REG_PC,uc.reg_read(arm.UC_ARM64_REG_X30));return
        return super().hook(uc,pc,size,user)


def expected(mode,kind,stage,selector):
    if mode==2:
        if kind==2:return ('3D',0x30,{0:0xc0,1:0x1b0}.get(selector,0x330),{0:0xd8,1:0x1c8}.get(selector,0x348))
        if kind==3 and stage in [4,5]:
            d={(4,0):(0,0x30),(4,1):(0x150,0x180),(5,0):(0x18,0x48),(5,1):(0x168,0x198)}
            return ('LMX',0x18,*d[(stage,selector)])
        if kind==1 and stage==8 and selector==0:return ('1D',0,0x60,0x78)
    else:
        if kind==2:return ('3D',0x30,0xc0 if selector==0 else 0x1b0,0xd8 if selector==0 else 0x1c8)
        if kind==3 and stage in [4,5,12]:
            d={(4,0):(0,0x30),(4,1):(0x150,0x180),(5,0):(0x18,0x48),(5,1):(0x168,0x198),(12,0):(0xf0,0x108),(12,1):(0x210,0x228)}
            return ('LMX',0x18,*d[(stage,selector)])
        if kind==1 and stage in [8,14] and (stage!=8 or selector==0):
            d={(8,0):(0x60,0x78),(14,0):(0x120,0x138),(14,1):(0x240,0x258)}
            return ('1D',0,*d[(stage,selector)])
    return None


def main():
    source=json.loads((HERE/'art-generator-source.json').read_text());m=MachO(source['path'])
    assert hashlib.sha256(m.file).hexdigest()==source['sha256']
    rows=[]
    for mode in [0,2]:
        for kind in [1,2,3]:
            for stage in [-1,4,5,8,12,14]:
                for selector in [0,1]:
                    g=DispatchGuest(m);controller=g.alloc(0x80);g.uc.mem_write(controller,struct.pack('<i',mode))
                    g.output=g.alloc(0x400);g.record=g.alloc(0xa0)
                    for off,value in [(0x48,3),(0x4c,3),(0x68,kind),(0x90,stage),(0x94,selector)]:g.uc.mem_write(g.record+off,struct.pack('<i',value))
                    vector=g.alloc(24);g.q(vector,g.record,g.record+0xa0,g.record+0xa0)
                    g.run(0x1b228,[controller,vector,g.output])
                    assert g.pairs==[[stage,selector]]
                    e=expected(mode,kind,stage,selector)
                    if e:
                        assert len(g.recorded)==1
                        actual=g.recorded[0]
                        assert tuple(actual[k] for k in ['kind','source_offset','parameter_data_offset','parameter_info_offset'])==e,(mode,kind,stage,selector,actual,e)
                    else:assert g.recorded==[]
                    rows.append(dict(controller_word=mode,type_word=kind,stage_word=stage,selector_word=selector,setters=g.recorded,pair=g.pairs[0],instructions=g.steps))
    result=dict(source_sha256=source['sha256'],entry='0x1b228',cases=rows,
                limits=['Original caller control-flow and output slot calculation only.',
                        'All three color setters are record-only hooks, not their implementations or pixel processing.',
                        'Descriptor vector insertion is recorded without allocation/mutation, since this caller does not reread it.',
                        'Controller and stage enum names beyond known function labels are not inferred.',
                        'Synthetic descriptors do not prove a real camera accepts or selects a corresponding ART.'])
    (HERE/'art-dispatch-guest-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({'cases':len(rows),'selected':sum(bool(r['setters']) for r in rows),'ignored':sum(not r['setters'] for r in rows),'exact_dispatch':True}))

if __name__=='__main__':main()
