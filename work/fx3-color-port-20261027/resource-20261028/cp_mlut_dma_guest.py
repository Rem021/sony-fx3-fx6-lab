#!/usr/bin/env python3
"""Original CP command dispatcher -> ID22 descriptors -> 70-entry DMA list."""
from hashlib import sha256
import json,struct
from unicorn import Uc,UC_ARCH_ARM,UC_MODE_THUMB,UC_HOOK_CODE,UC_HOOK_MEM_WRITE
from unicorn import arm_const as R
from vfx_resource_guest import HERE,image,BASE,PIN,STACK,DATA,STOP,CALLBACK

PROFILE=0x2015794
LLI=0x2025570
SHADOW=0x2025554
SPANS=[(0x368ec0,0x369114),(0x916d26,0x916dec),(0x90e1b6,0x90e1c2),
       (0x90e1d0,0x90e1dc),(0x9113ea,0x911434),(0x90c11e,0x90c134),(0x911448,0x911462)]


def main():
    b=image();profile=(HERE.parent/'route-20261028/CP-look22-initialized.bin').read_bytes()
    assert len(profile)==70*140 and sha256(profile).hexdigest()=='a4f057164b12be25a2e9e80bcdd6e78bffe3d7685606e8dde39d22b1e98c10e0'
    source=json.loads((HERE/'vfx-resource-results.json').read_text())
    u=Uc(UC_ARCH_ARM,UC_MODE_THUMB);u.mem_map(BASE,(len(b)+4095)&~4095);u.mem_write(BASE,b)
    for a,n in [(STACK,0x10000),(DATA,0x3000),(STOP,0x1000),(0x2015000,0x1b000),(0x147d000,0x1000)]:u.mem_map(a,n)
    # Declared log mode 3 suppresses diagnostics, including the MMIO register dump.
    u.mem_write(PROFILE,profile);u.mem_write(0xf42e18,struct.pack('<I',3))
    translated=[];flushes=[];submits=[];count=[0];queue_return=[0]
    def ret(value):
        u.reg_write(R.UC_ARM_REG_R0,value&0xffffffff);u.reg_write(R.UC_ARM_REG_PC,u.reg_read(R.UC_ARM_REG_LR))
    def code(u,pc,size,unused):
        if pc==STOP:u.emu_stop();return
        if pc==0x538a28:
            address=u.reg_read(R.UC_ARM_REG_R0);translated.append(address)
            # Declared identity translation, not the device's live mapping/provider.
            ret(address);return
        if pc==0x540320:
            args=[u.reg_read(R.UC_ARM_REG_R0),u.reg_read(R.UC_ARM_REG_R1)]
            assert args[1]==16;flushes.append(args);ret(0);return
        if pc==0xa1f0d2:
            args=[u.reg_read(R.UC_ARM_REG_R0),u.reg_read(R.UC_ARM_REG_R1)]
            assert args==[LLI,CALLBACK]
            submits.append(args);ret(queue_return[0]);return
        off=pc-BASE;assert any(a<=off<z for a,z in SPANS),hex(pc);count[0]+=1
    def write(u,access,address,size,value,unused):
        assert (STACK<=address and address+size<=STACK+0x10000 or
                LLI<=address and address+size<=LLI+70*16 or
                SHADOW<=address and address+size<=SHADOW+7*4),hex(address)
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    def run(command,outcome=0):
        group=command[2];u.mem_write(DATA,struct.pack('<14I',*command))
        u.mem_write(LLI-16,b'\xa7'*(70*16+32));u.mem_write(SHADOW,b'\xa7'*28)
        # SHADOW ends at LLI; an independent guard lives before SHADOW.
        u.mem_write(SHADOW-16,b'\xa7'*16)
        queue_return[0]=outcome;begin=[len(translated),len(flushes),len(submits)]
        for i in range(4):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),DATA if i==0 else 0)
        for i in range(4,12):u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
        u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000);u.reg_write(R.UC_ARM_REG_LR,STOP|1)
        u.emu_start((BASE+0x368ec0)|1,STOP+4,count=25000)
        assert u.reg_read(R.UC_ARM_REG_PC)==STOP and u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
        assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))
        raw=bytes(u.mem_read(LLI,70*16));words=list(struct.iter_unpack('<4I',raw))
        register_base=0xf4009000+(group<<20)
        for i,(src,dst,nxt,ctl) in enumerate(words):
            source_va,register_offset,count_words=struct.unpack_from('<3I',profile,i*140)
            assert src==source_va and dst==register_base+register_offset
            assert nxt==(LLI+(i+1)*16 if i<69 else 0)
            assert ctl==0x0e489000|count_words|(0x80000000 if i==69 else 0)
        assert len(flushes)-begin[1]==70 and len(submits)-begin[2]==1
        assert bytes(u.mem_read(LLI+70*16,16))==b'\xa7'*16
        assert bytes(u.mem_read(SHADOW-16,16))==b'\xa7'*16
        shadows=list(struct.unpack('<7I',u.mem_read(SHADOW,28)))
        assert shadows==[22 if i==group and outcome==0 else 0xa7a7a7a7 for i in range(7)]
        path=HERE/f'cp-look22-group{group}-lli.bin'
        if outcome==0:path.write_bytes(raw)
        return dict(group=group,register_base=hex(register_base),entries=70,
                    source_command=command,lli_sha256=sha256(raw).hexdigest(),
                    first=list(words[0]),last=list(words[-1]),
                    translation_provider_calls=len(translated)-begin[0],cache_flush_calls=len(flushes)-begin[1],
                    declared_submit_outcome=outcome,software_look_shadow=shadows)
    commands={x['commands'][0][2]:x['commands'][0] for x in source['successful_sets']}
    assert set(commands)==set(range(7))
    cases=[run(commands[i]) for i in range(7)]
    failed=run(commands[0],7)
    result=dict(status='PASS_ORIGINAL_CP_DISPATCH_ID22_DMA_ALL_RESOURCE_GROUPS',cp_sha256=PIN,
                initialized_profile_sha256=sha256(profile).hexdigest(),cases=cases,submit_failure_probe=failed,
                original_instructions=count[0],source_spans=[dict(file_start=hex(a),file_end_exclusive=hex(z),sha256=sha256(b[a:z]).hexdigest()) for a,z in SPANS],
                runtime_fixtures={'diagnostic_control_raw':3,'look_override_flag_raw':0},
                scope='Original command dispatcher, lookup, register-base calculation and DMA-list construction. Commands are host-fed from the preceding guest boundary; actual queue transport does not execute. Identity address translation, cache flush and DMA submit outcomes are declared. No MMIO writes, real physical addresses, hardware DMA, callback or pixel results.',
                runtime_payload_limit='Three original descriptor sources point to unobserved runtime selector words; lists preserve their addresses without claiming their values.')
    (HERE/'cp-mlut-dma-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'groups',len(cases),'entries per group',70,'original instructions',count[0])


if __name__=='__main__':main()
