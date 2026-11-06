#!/usr/bin/env python3
"""Pin original producer, allocation and consumer slices plus graph table identities."""
import csv,json,struct
from hashlib import sha256
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
from resource_binding_guest import Guest,HERE,image,BASE,PIN,SPANS,names
from caller_binding_guest import EXTRA_SPANS,SDK_SPANS
from context_binding_guest import PRODUCER_SPANS


def main():
    b=image();g=Guest(b);labels=names(b);nodes=[]
    lower=list(struct.unpack_from('<10I',b,0xb4e560-BASE))
    upper=list(struct.unpack_from('<10I',b,0xb4e590-BASE))
    preferences=list(struct.unpack_from('<10I',b,0xb4e530-BASE))
    expected=[0xf15398,0xf15e24,0xf168b0,0xf1733c,0xf15398,0xf15398,0xf15398,0xf17dc8,0xf18854,0xf17dc8]
    for node in range(1,11):
        va=g.call(0x3c7294,[node]);assert va==expected[node-1]
        raw=b[va-BASE:va-BASE+25*108];rows=[]
        for kind in range(25):
            row=raw[kind*108:(kind+1)*108];enabled=row[0];rid=struct.unpack_from('<I',row,4)[0]
            assert enabled in [0,1] and rid<71
            rows.append(dict(kind=kind,enabled=enabled,resource_id=rid,
                             name=labels[rid] if enabled else None,raw_row_sha256=sha256(row).hexdigest()))
        nodes.append(dict(node=node,table_va=hex(va),file_offset=hex(va-BASE),bytes=len(raw),
                          sha256=sha256(raw).hexdigest(),rows=rows))
    out=HERE/'disassembly';out.mkdir(exist_ok=True);source=[]
    spans=sorted(set(SPANS+EXTRA_SPANS+SDK_SPANS+PRODUCER_SPANS+[(0x30020c,0x3004ca),(0x300ea2,0x301062),
                (0x306c18,0x306cb2),(0x3084d4,0x3085c8),(0x30a43c,0x30a530)]))
    cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    for a,z in spans:
        name=f'cp-{a:08x}-{z:08x}.txt'
        (out/name).write_text('\n'.join(f'{i.address-BASE:08x}: {i.mnemonic} {i.op_str}' for i in cs.disasm(b[a:z],BASE+a))+'\n')
        source.append(dict(file_start=hex(a),end_exclusive=hex(z),sha256=sha256(b[a:z]).hexdigest(),
                           disassembly='disassembly/'+name))
    with (HERE/'graph-node-resources.csv').open('w',newline='') as f:
        w=csv.writer(f);w.writerow(['node','table_va','kind_raw','enabled','resource_id','name_if_enabled'])
        for n in nodes:
            for r in n['rows']:w.writerow([n['node'],n['table_va'],r['kind'],r['enabled'],r['resource_id'],r['name']])
    result=dict(status='PASS_PINNED_CONTEXT_AND_RESOURCE_BINDING_INVENTORY',cp_sha256=PIN,
                source_spans=source,graph_nodes=nodes,
                graph_contexts=[dict(context_raw=i+1,node_lower=lower[i],node_upper=upper[i],
                                     wrapper_preference_raw=preferences[i]) for i in range(10)],
                diagnostic_strings=[dict(va=hex(va),value=b[va-BASE:b.index(0,va-BASE)].decode())
                                    for va in [0xd9ab49,0xdf2544]],
                cautions=['Disassembly excerpts include embedded jump tables. Linear decoding of a table is not evidence of instructions executed.',
                          'The 0x306c18/0x3084d4/0x30a43c caller slices are static comparison candidates, not executed whole-function paths.',
                          'Wrapper preference IDs differ from final driver groups for combined contexts. Raw graph nodes and context enums are not assigned MAIN/monitor meaning.',
                          'Resource ID 22 is GRP05_VFX. Look ID 22 is MLUT_LOOKNAME_SL3SG3_TO_ACESREC709. Their equal integer values do not establish a relationship.'])
    (HERE/'static-inventory-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'source slices',len(source),'node rows',sum(len(n['rows']) for n in nodes))


if __name__=='__main__':main()
