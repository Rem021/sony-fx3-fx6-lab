#!/usr/bin/env python3
"""Original header facts, source windows and ordinary-return control-flow audit."""
import hashlib,json,struct,sys
from pathlib import Path
sys.dont_write_bytecode=True
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from backup_state_guest import inputs,PREVIOUS,old
HERE=Path(__file__).resolve().parent
def sha(b):return hashlib.sha256(b).hexdigest()
def main():
    out=HERE/'backup-and-file-open-source-review.json';assert not out.exists()
    raw,record,source,bank=inputs();BASE=old.BASE
    header_facts=[];FDAT=Path(source['FDAT_source'])
    members={r['member']:r for r in source['original_member_provenance']}
    for template in source['templates']:
        member=members[template['member']]
        with FDAT.open('rb') as f:
            f.seek(member['FDAT_offset']-512);header=f.read(512);assert sha(header)==member['header_sha256']
            data=f.read(member['bytes']);assert sha(data)==member['sha256']==template['sha256']
        for b in template['banks']:
            at=int(b['template_record_offset'],16)
            dataoff,datasize=struct.unpack_from('<2I',data,at+24);n=dataoff+datasize
            r=data[at:at+n];assert sha(r)==b['record_sha256']
            assert (sum(r[:32])+sum(r[36:]))&0xffffffff==struct.unpack_from('<I',r,32)[0]
            header_facts.append(dict(template=template['member'],record_index=b['bank'],record_sha256=sha(r),
                header_sha256=sha(r[:256]),word4=hex(struct.unpack_from('<I',r,4)[0]),
                byte8=r[8],word2c_signed=struct.unpack_from('<i',r,0x2c)[0],marker_hex=r[12:16].hex()))
    assert len(header_facts)==44 and all(x['byte8']==0 for x in header_facts)
    originals=HERE/'original-files';originals.mkdir(exist_ok=True)
    f=originals/'CP-template-header.bin';assert not f.exists();f.write_bytes(record[:256])
    ctype=raw[0xfe06147d-BASE:0xfe06147d-BASE+256]
    f=originals/'NOR-character-class-table.bin';assert not f.exists();f.write_bytes(ctype)
    assert all(ctype[x]&8 for x in range(97,123)) and all(not(ctype[x]&8) for x in range(65,91))
    folder=HERE/'source-fragments';folder.mkdir(exist_ok=True);fragments=[]
    cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);cs.detail=True
    windows=[(0xfe04c76c,0xfe04c7b4),(0xfe04d584,0xfe04d63c),(0xfe04d63c,0xfe04d69c),
        (0xfe058adc,0xfe058b5c),(0xfe058894,0xfe0588a4),(0xfe058cf0,0xfe058f50),
        (0xfe058b7c,0xfe058c94),(0xfe0545dc,0xfe054a18),(0xfe057fa0,0xfe058178),
        (0xfe057e98,0xfe057f0c),(0xfe04a3b0,0xfe04a490),(0xfe04a548,0xfe04a5a4),
        (0xfe0561b4,0xfe056320)]
    for lo,hi in windows:
        data=raw[lo-BASE:hi-BASE];decoded=list(cs.disasm(data,lo));assert sum(x.size for x in decoded)==len(data)
        f=folder/f'{lo:08x}-{hi:08x}.txt';assert not f.exists()
        f.write_text('\n'.join(f'{x.address:08x} {x.bytes.hex()} {x.mnemonic:8} {x.op_str}' for x in decoded)+'\n')
        fragments.append(dict(VA=hex(lo),end_exclusive=hex(hi),bytes=len(data),original_bytes_sha256=sha(data),listing=str(f.relative_to(HERE))))
    entry=0xfe057fa0;end=0xfe058178
    instructions=list(cs.disasm(raw[entry-BASE:end-BASE],entry));nodes={x.address:x for x in instructions}
    successors={};calls=[];returns=[]
    conditional=lambda mn:mn.startswith('b.') or mn in ['cbz','cbnz','tbz','tbnz']
    for x in instructions:
        following=x.address+4
        if x.mnemonic=='ret':successors[x.address]=[];returns.append(x.address)
        elif x.mnemonic=='b' or conditional(x.mnemonic):
            target=x.operands[-1].imm;assert target in nodes
            successors[x.address]=[target]+([following] if conditional(x.mnemonic) else [])
        else:
            assert x.mnemonic not in ['br','blr','eret']
            successors[x.address]=[following] if following<end else []
            if x.mnemonic=='bl':calls.append(dict(PC=hex(x.address),target=hex(x.operands[0].imm)))
    reachable={entry};pending=[entry]
    while pending:
        at=pending.pop()
        for target in successors[at]:
            if target not in reachable:reachable.add(target);pending.append(target)
    dom={x:({entry} if x==entry else set(reachable)) for x in reachable}
    changed=True
    while changed:
        changed=False
        for node in reachable-{entry}:
            predecessors=[p for p in reachable if node in successors[p]];assert predecessors
            new={node}|set.intersection(*(dom[p] for p in predecessors))
            if new!=dom[node]:dom[node]=new;changed=True
    assert returns==[0xfe058174]
    assignment=nodes[0xfe05816c];assert assignment.mnemonic=='mov' and assignment.op_str=='w0, #-0x198'
    assert all(0xfe05816c in dom[x] for x in returns)
    assert '0xfe058178' not in [x['target'] for x in calls]
    result=dict(NOR_sha256=sha(raw),source_fragments=fragments,official_header_facts=header_facts,
        selector_contract=dict(header_fields=['word+4','byte+8','signed word+0x2c'],
            original_file_selector_wrapper='0xfe04c7a8 sets W2=1',helper='0xfe04d584',
            original_checker='0xfe04c76c',RAM_reuse_consumer='0xfe058d40..0xfe058dfc',
            scope='File choice and RAM reuse are separate original code paths; rejection in one must not be generalized to all startup routes.'),
        file_open_control_flow=dict(entry=hex(entry),end_exclusive=hex(end),instructions=len(instructions),reachable_instructions=len(reachable),
            return_addresses=list(map(hex,returns)),return_assignment=dict(PC=hex(assignment.address),instruction=assignment.mnemonic+' '+assignment.op_str,
                signed_W0=-408),assignment_dominates_all_ordinary_returns=True,ordinary_call_targets=calls,
            original_byte_stream_reader_called=False,
            analysis_scope='Bounded intraprocedural CFG; ordinary calls are assumed to return to their next instruction. No claim about exceptions, nonlocal control transfer, unrelated loader builds or other camera boot routes.'),
        declared_ctype_source=dict(VA='0xfe06147d',bytes=256,sha256=sha(ctype),source='Unchanged original NOR bytes; explicit fixture pointer, not recovered normal locale initialization.'),
        scope='Original source/official defaults and isolated guest results only. No complete camera backup, actual file I/O, physical pixels, normal boot or flash admission is proved.')
    out.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(source_fragments=len(fragments),official_header_count=len(header_facts),all_default_byte8_zero=True,
        file_open=result['file_open_control_flow'])))
if __name__=='__main__':main()
