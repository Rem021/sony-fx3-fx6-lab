#!/usr/bin/env python3
"""Run only 25 original x86 header-check bytes in isolated Unicorn RAM.

This is a branch-fragment check with an explicitly supplied 16-byte buffer.
No DLL loader/constructor, file adapter, decryption, camera service or OS is run.
"""
import hashlib,json,sys
from pathlib import Path
sys.dont_write_bytecode=True
from pe_reader import PE
from capstone import Cs,CS_ARCH_X86,CS_MODE_32
from unicorn import Uc,UC_ARCH_X86,UC_MODE_32,UC_HOOK_CODE,UC_PROT_READ,UC_PROT_WRITE,UC_PROT_EXEC
from unicorn.x86_const import UC_X86_REG_ESI,UC_X86_REG_EIP
HERE=Path(__file__).resolve().parent;TASK=HERE.parent
PIN='a96aecd93432bded2d90a116338082fffe42d302af899bd18f547d2e91e365c8'
START=0x1001fbb0;END=0x1001fbc9;DATA=0x30000000
STOPS={0x1001fd3f:'invalid_signature_branch',0x1001fc19:'prefix_accepted_before_timestamp',0x1001fbc9:'unsupported_version_branch'}
def run(pe,raw,fragment,allowed,name,header,expected):
    u=Uc(UC_ARCH_X86,UC_MODE_32)
    size=(max(s['VA']+max(s['virtual_size'],s['raw_size']) for s in pe.sections)+4095)//4096*4096
    u.mem_map(pe.base,size,UC_PROT_READ|UC_PROT_WRITE|UC_PROT_EXEC);u.mem_write(pe.base,raw[:pe.headers])
    for s in pe.sections:u.mem_write(pe.base+s['VA'],raw[s['raw_offset']:s['raw_offset']+s['raw_size']])
    u.mem_protect(pe.base,size,UC_PROT_READ|UC_PROT_EXEC)
    u.mem_map(DATA,4096,UC_PROT_READ|UC_PROT_WRITE);u.mem_write(DATA,header);u.mem_protect(DATA,4096,UC_PROT_READ)
    u.reg_write(UC_X86_REG_ESI,DATA);trace=[];result={}
    def hook(uc,address,size,user):
        assert address in allowed or address in STOPS,hex(address)
        trace.append(hex(address))
        if address in STOPS:result['stop']=STOPS[address];uc.emu_stop()
    u.hook_add(UC_HOOK_CODE,hook)
    u.emu_start(START,pe.base+size,timeout=200000,count=64)
    assert result.get('stop')==expected,(name,result,hex(u.reg_read(UC_X86_REG_EIP)))
    assert bytes(u.mem_read(DATA,len(header)))==header
    assert bytes(u.mem_read(START,len(fragment)))==fragment
    return dict(name=name,input_first16_hex=header.hex(),expected=expected,observed=result['stop'],trace=trace,
        instructions_before_stop=len(trace)-1,original_code_and_input_unchanged=True)
def main():
    out=HERE/'svu-header-guest-results.json';assert not out.exists()
    raw=(HERE/'host-components/sncverup_tool.dll').read_bytes();assert hashlib.sha256(raw).hexdigest()==PIN
    pe=PE(raw);at=pe.off(START-pe.base,END-START);fragment=raw[at:at+END-START]
    ins=list(Cs(CS_ARCH_X86,CS_MODE_32).disasm(fragment,START));assert sum(i.size for i in ins)==len(fragment)==25
    assert [i.mnemonic for i in ins]==['cmp','jne','cmp','jne','cmp','je']
    svu=HERE/'host-components/sncverup_tool.svu'
    with svu.open('rb') as f:own=f.read(16)
    assert own[:3]==b'VU\x01'
    inputs=[('SNC_original_SVU_prefix',own,'prefix_accepted_before_timestamp'),
        ('synthetic_VU_version2',b'VU\x02'+bytes(13),'unsupported_version_branch'),
        ('synthetic_wrong_first',b'XU\x01'+bytes(13),'invalid_signature_branch'),
        ('synthetic_wrong_second',b'VX\x01'+bytes(13),'invalid_signature_branch')]
    sources=[('VENICE_V201',TASK/'donor-loader-20261029/outer-members/VENICE/DATA23213'),
        ('VENICE_V630',TASK/'donor-venice1-20261029/outer-members/VENICE/DATA23213')]
    old=json.loads((TASK/'donor-20261028/donor-inner-source-inventory.json').read_text())['files']
    sources += [('VENICE2_'+r['version'],Path(r['path'])) for r in old]
    for name,p in sources:
        with p.open('rb') as f:header=f.read(16)
        inputs.append((name,header,'invalid_signature_branch'))
    results=[run(pe,raw,fragment,{i.address for i in ins},*x) for x in inputs]
    record=dict(source_DLL_sha256=PIN,fragment_VA=hex(START),fragment_file_offset=at,fragment_bytes=fragment.hex(),
        fragment_SHA256=hashlib.sha256(fragment).hexdigest(),disassembly=[dict(VA=hex(i.address),bytes=i.bytes.hex(),mnemonic=i.mnemonic,operands=i.op_str) for i in ins],
        cases=results,native_Sony_programs_executed=0,device_actions=0,
        scope='Isolated RAM execution of original six-instruction header fragment only. Caller read/alloc/constructor and later timestamp/decryption excluded. Passing VU1 is not a valid whole SVU file, successful firmware parse or flashing acceptance. Rejection here is not proof the entire host tool lacks another reader.')
    out.write_text(json.dumps(record,indent=2)+'\n')
    print(json.dumps(dict(cases=len(results),fragment_bytes=len(fragment),original_SVU='prefix accepted only',VENICE_original_prefixes_rejected=len(sources),whole_VENICE_reader_recovered=False,device_actions=0)))
if __name__=='__main__':main()
