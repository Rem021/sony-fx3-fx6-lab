#!/usr/bin/env python3
"""Recovered ownership contract: occupied slots, namespaces and generation counters."""
import json,struct
from resource_binding_guest import Guest,HERE,image,PIN,DATA,OWNERS

MASKS=[1,2,4,8,15,3,12]


def main():
    b=image();g=Guest(b);availability=[];allocations=[]
    # Explicit group requests 3..9 map through the original table to SDK groups.
    request_groups={3:0,4:1,5:2,6:3,7:5,8:6,9:4}
    for occupied in range(16):
        for request,group in request_groups.items():
            rows=[(0x1234,1 if occupied>>i&1 else 0) for i in range(4)]
            before=struct.pack('<8I',*[x for row in rows for x in row]);g.u.mem_write(OWNERS,before)
            g.u.mem_write(DATA+0x100,struct.pack('<II',0xa7a7a7a7,0xa7a7a7a7))
            status=g.call(0x487a74,[request,DATA+0x100,DATA+0x104])
            values=list(struct.unpack('<II',g.u.mem_read(DATA+0x100,8)))
            blocked=bool(occupied&MASKS[group])
            assert status==(3 if blocked else 0)
            assert values==([0xa7a7a7a7]*2 if blocked else [request,group])
            assert bytes(g.u.mem_read(OWNERS,32))==before
            availability.append(dict(occupied_slot_mask=occupied,request=request,driver_group=group,
                                     status=status,output_unchanged=blocked))
    for group,mask in enumerate(MASKS):
        for namespace in [0,1]:
            for flag in [0,1]:
                for previous in [0,41]:
                    g.u.mem_write(OWNERS,struct.pack('<8I',*sum(([previous,0] for _ in range(4)),[])))
                    g.u.mem_write(DATA+0x100,struct.pack('<I',0xa7a7a7a7))
                    status=g.call(0x487be0,[namespace,DATA+0x100,group,flag])
                    owner=struct.unpack('<I',g.u.mem_read(DATA+0x100,4))[0]
                    expected=(previous+1)|(group<<16)|(0 if flag else 0x80000000)
                    assert status==0 and owner==expected
                    rows=list(struct.iter_unpack('<II',g.u.mem_read(OWNERS,32)))
                    assert rows==[(owner,namespace+1) if mask>>i&1 else (previous,0) for i in range(4)]
                    resolver=g.call(0x488094,[namespace,owner,DATA+0x104])
                    resolved=struct.unpack('<I',g.u.mem_read(DATA+0x104,4))[0]
                    assert resolver==0 and resolved==group
                    allocations.append(dict(driver_group=group,slot_mask=mask,namespace=namespace,flag=flag,
                                            previous_counter=previous,computed_owner=hex(owner),owner_rows=rows,
                                            resolver_status=resolver,resolved_group=resolved))
    result=dict(status='PASS_ORIGINAL_OWNER_AVAILABILITY_AND_GENERATION_BOUNDARIES',cp_sha256=PIN,
                availability_cases=availability,allocation_cases=allocations,original_instructions=g.instructions,
                scope='Declared free/occupied owner table states and success lock returns. Original availability, owner allocator and namespace resolver execute. The allocator is deliberately tested after availability; it does not independently reject occupied rows. No hardware initialization or camera RAM state is established.')
    (HERE/'owner-boundaries-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'availability',len(availability),'allocations',len(allocations),'original instructions',g.instructions)


if __name__=='__main__':main()
