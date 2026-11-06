#!/usr/bin/env python3
"""Original software table initialization in Unicorn RAM, with no physical MMU."""
import hashlib, importlib.util, json, struct, sys
from pathlib import Path
sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
PREVIOUS = HERE.parent / 'cp-bootstrap-20261029'
HELPER = PREVIOUS / 'bootstrap_guest.py'
assert hashlib.sha256(HELPER.read_bytes()).hexdigest() == 'bf76efb2c8633e648292ce52f7754fa1b3da6fbddcbf331bec9fb81450a7d2ca'
spec = importlib.util.spec_from_file_location('original_bootstrap_guest', HELPER)
old = importlib.util.module_from_spec(spec)
spec.loader.exec_module(old)
R = old.R
class SoftwareGuest(old.Guest):
    def __init__(self, raw, flag=0):
        self.allowed_barriers = []
        self.mapping_calls = []
        super().__init__(raw, flag)
    def code(self, u, pc, size, user):
        # Execute this original DSB in Unicorn only. It has no external observer,
        # cache or physical TLB to synchronize. Other CPU/privileged gates stay.
        if pc == 0x5541e4:
            assert bytes(u.mem_read(pc, 4)) == bytes.fromhex('4ff07ff5')
            self.allowed_barriers.append(dict(PC=hex(pc), instruction='dsb sy',
                scope='Original opcode executed in Unicorn RAM; physical ordering/cache/TLB effects are not modeled.'))
            self.instructions += 1
            return
        if pc == 0x553fe8:
            self.mapping_calls.append(dict(
                arguments=[hex(u.reg_read(getattr(R, f'UC_ARM_REG_R{i}'))) for i in range(4)],
                context_word=hex(struct.unpack('<I', bytes(u.mem_read(u.reg_read(R.UC_ARM_REG_SP), 4)))[0])))
        super().code(u, pc, size, user)
def snapshot(g, name):
    output=[]
    for address in [0x09a08e00,0x09a21e00,0x09000000,0x0fffffff,0x10000000,0x128000,0]:
        at=old.STACK+0x8000
        g.u.mem_write(at,b'\xa7'*4)
        query=g.call(0x54bbd0,[address,at])
        pointer=g.call(0x53894c,[address])
        output.append(dict(address=hex(address),attribute_call=query,
            attributes=hex(g.words(at,1)[0]),pointer_call=pointer))
    return dict(name=name,cases=output)
def main():
    out=HERE/'software-init-results.json';assert not out.exists()
    raw=old.SOURCE.read_bytes();assert hashlib.sha256(raw).hexdigest()==old.PIN
    strict=old.Guest(raw,0)
    strict_boot=strict.call(0x1083a4,stops={0x108728:'before_CPU_setup_call'})
    assert strict_boot['boundary']['PC']=='0x108728'
    strict_init=strict.call(0x553d48,[old.ROOT])
    assert strict_init['boundary']['PC']=='0x5541e4'
    before=snapshot(strict,'strict_pre_first_DSB_snapshot')
    g=SoftwareGuest(raw)
    boot=g.call(0x1083a4,stops={0x108728:'before_CPU_setup_call'})
    assert boot['boundary']['PC']=='0x108728'
    l1_before=bytes(g.u.mem_read(0x14e8000,0x4000))
    init=g.call(0x553d48,[old.ROOT])
    after=snapshot(g,'original_software_initializer_result_RAM_only')
    l1_after=bytes(g.u.mem_read(0x14e8000,0x4000))
    changed=[]
    for i,(a,b) in enumerate(zip(struct.unpack('<4096I',l1_before),struct.unpack('<4096I',l1_after))):
        if a!=b:changed.append(dict(index=hex(i),VA=hex(i<<20),before=hex(a),after=hex(b)))
    results=dict(CP_source=str(old.SOURCE),CP_sha256=old.PIN,
        strict_boot=strict_boot,strict_init=strict_init,bootstrap=boot,software_initializer=init,
        original_mapping_calls=g.mapping_calls,modeled_DSB_events=g.allowed_barriers,
        snapshots=[before,after],L1_changed_entries=changed,
        scope='Isolated original CP instructions with the declared optional flag0 and an independent post-poll stack. The original DSB opcode is executed only in the software emulator. No CPU setup, physical page walk/cache/TLB ordering, original startup poll, native Sony process, DmmCfg candidate load, buffer or RAW pixels is proved.')
    out.write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(dict(boundary=init['boundary'],instructions=init['original_instructions'],
        writes=init['original_RAM_writes'],mapping_calls=len(g.mapping_calls),
        DSB_events=len(g.allowed_barriers),L1_changed_entries=len(changed),
        query_results=[dict(snapshot=s['name'],cases=[dict(address=x['address'],attributes=x['attributes'],
            query_R0=x['attribute_call']['registers'][0],pointer_R0=x['pointer_call']['registers'][0]) for x in s['cases']]) for s in [before,after]])))
if __name__=='__main__':main()
