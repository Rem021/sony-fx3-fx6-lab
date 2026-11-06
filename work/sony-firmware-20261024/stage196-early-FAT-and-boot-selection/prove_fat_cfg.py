"""Conservative normal-return CFG proof for the original NOR FAT-open entry.

Calls are not executed. Their ordinary ABI return edge is assumed; nonlocal
abort/exception/hardware effects and whole-boot reachability are not proven.
"""
from pathlib import Path
from hashlib import sha256
import json
from capstone import Cs,CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN
from capstone.arm64 import ARM64_OP_IMM
HERE=Path(__file__).resolve().parent;BASE=HERE.parent
SOURCE=BASE/'stage182-boot-selector-and-recovery-admission/current-updater-evidence/nor-loader-members/loader_nor.bin'
data=SOURCE.read_bytes();expected='4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942';assert sha256(data).hexdigest()==expected
base=0xfe049000;start=0xfe057fa0;end=0xfe058178
cs=Cs(CS_ARCH_ARM64,CS_MODE_LITTLE_ENDIAN);cs.detail=True
raw=data[start-base:end-base];ins={i.address:i for i in cs.disasm(raw,start)}
assert len(ins)*4==len(raw)
edges={};calls=[];unknown=[]
for address,i in ins.items():
    if i.mnemonic=='ret':succ=[]
    elif i.mnemonic=='b':succ=[i.operands[0].imm]
    elif i.mnemonic.startswith('b.') or i.mnemonic in ('cbz','cbnz','tbz','tbnz'):succ=[i.operands[-1].imm,address+4]
    elif i.mnemonic=='bl':
        calls.append({'site':hex(address),'target':hex(i.operands[0].imm),'assumption':'normal ABI return to next instruction; not executed'})
        succ=[address+4]
    elif i.mnemonic in ('br','blr','eret','drps'):unknown.append(hex(address));succ=[]
    else:succ=[address+4]
    if any(t not in ins for t in succ):unknown.append({'site':hex(address),'out_of_function_edges':[hex(t) for t in succ if t not in ins]})
    edges[address]=succ
assert not unknown,unknown
reachable=set();todo=[start]
while todo:
    n=todo.pop()
    if n not in reachable:reachable.add(n);todo.extend(edges[n])
pred={a:set() for a in reachable}
for a in reachable:
    for b in edges[a]:pred[b].add(a)
dominators={a:({start} if a==start else set(reachable)) for a in reachable}
changed=True
while changed:
    changed=False
    for a in sorted(reachable):
        if a==start:continue
        common=set.intersection(*(dominators[p] for p in pred[a])) if pred[a] else set()
        new=common|{a}
        if new!=dominators[a]:dominators[a]=new;changed=True
returns=[a for a in reachable if ins[a].mnemonic=='ret'];setter=0xfe05816c
assert returns==[0xfe058174]
assert setter in dominators[returns[0]] and ins[setter].mnemonic=='mov' and ins[setter].op_str=='w0, #-0x198'
assert ins[setter+4].mnemonic=='add' and ins[setter+8].mnemonic=='ret'
proof={'source':str(SOURCE),'sha256':expected,'configured_base':hex(base),'entry':hex(start),'end_exclusive':hex(end),
       'entry_xref':{'caller':'0xfe053cf8','kind':'bl','context':'mode existence fallback'},
       'raw_sha256':sha256(raw).hexdigest(),'instructions':len(ins),'reachable_instructions':len(reachable),
       'normal_returns':[hex(x) for x in returns],'dominating_return_setter':hex(setter),'normal_return_signed32':-408,
       'unknown_or_outside_tail_edges':unknown,'call_assumptions':calls,
       'conclusion':'Every modeled ordinary return from this exact original FAT-open entry returns-408. No success return was found; does not prove callees return, hardware initialization, or whole-device boot behavior.',
       'scope':'host static CFG only; no Sony/guest/device execution'}
with (HERE/'fat-open-normal-return-proof.json').open('x') as f:json.dump(proof,f,indent=2);f.write('\n')
with (HERE/'fat-open-selected-original.txt').open('x') as f:
    for a,i in ins.items():f.write(f'{a:#x} [file+{a-base:#x}] {i.bytes.hex()} {i.mnemonic:8} {i.op_str}\n')
with (HERE/'fat-open-cfg.json').open('x') as f:json.dump({'edges':{hex(a):[hex(b) for b in e] for a,e in edges.items()},'return_dominators':[hex(x) for x in sorted(dominators[returns[0]])]},f,indent=2);f.write('\n')
print(json.dumps({k:proof[k] for k in ('instructions','reachable_instructions','normal_returns','dominating_return_setter','normal_return_signed32')}))
