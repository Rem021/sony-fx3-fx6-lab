#!/usr/bin/env python3
"""Original CP EC mode transitions and capture gate, bounded CPU fixtures only."""
from pathlib import Path
from hashlib import sha256
import sys, json, struct
from capstone import Cs, CS_ARCH_ARM, CS_MODE_THUMB
from unicorn import Uc, UC_ARCH_ARM, UC_MODE_THUMB, UC_HOOK_CODE, UC_HOOK_MEM_WRITE
from unicorn import arm_const as R

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent/'route-20261028'))
from cp_look_route import image, BASE, PIN
from ap_cp_message import PARAM, STACK, DATA, STOP

TABLE, CURRENT = 0xbf29ac, 0xf06510
DISPATCH, DISPATCH_END = 0x6721a0, 0x6721f4


def get_records(b):
    out = []
    for i, ptr in enumerate(struct.unpack_from('<19I', b, TABLE-BASE)):
        record = struct.unpack_from('<6I', b, ptr-BASE)
        assert record[0] == i and record[5] & 1
        out.append(dict(id=i, address=ptr, enter=record[1], leave=record[2],
                        update=record[3], extra=record[4], transition=record[5]))
    assert struct.unpack_from('<I', b, TABLE-BASE+19*4)[0] == 0x80
    return out


def setup(b):
    u = Uc(UC_ARCH_ARM, UC_MODE_THUMB)
    u.mem_map(BASE, (len(b)+4095)&~4095); u.mem_write(BASE, b)
    for a,n in [(STACK,0x10000),(DATA,0x6000),(STOP,0x1000),(0x143c000,0x2000),
                (PARAM&~4095,0x3000)]: u.mem_map(a,n)
    return u


def prepare(u):
    for i in range(4): u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0)
    for i in range(4,12): u.reg_write(getattr(R,f'UC_ARM_REG_R{i}'),0x77770000+i)
    u.reg_write(R.UC_ARM_REG_SP,STACK+0xf000); u.reg_write(R.UC_ARM_REG_LR,STOP|1)


def preserved(u):
    assert u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
    assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in range(4,12))


def transitions(b,records):
    u=setup(b); count=[0]; callbacks=[]; direct=[True]
    cs=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
    ranges=[]
    for r in records:
        start=(r['transition']&~1)-BASE
        end=None
        for ins in cs.disasm(b[start:start+0x200],BASE+start):
            if ins.mnemonic=='bx' and ins.op_str=='lr':
                end=ins.address+ins.size;break
        # Handler 10 has an early return before its remaining branch targets.
        if r['id']==10: end=BASE+0x1d41e8
        assert end is not None,hex(start)
        ranges.append((BASE+start,end))
    lifecycle={r[k]&~1 for r in records for k in ['enter','leave'] if r[k]}
    def code(u,pc,size,unused):
        if pc==STOP: u.emu_stop();return
        if pc in lifecycle:
            assert not direct[0]
            callbacks.append(dict(address=hex(pc),r0=hex(u.reg_read(R.UC_ARM_REG_R0))))
            u.reg_write(R.UC_ARM_REG_PC,u.reg_read(R.UC_ARM_REG_LR));return
        assert BASE+DISPATCH<=pc<BASE+DISPATCH_END or any(a<=pc<z for a,z in ranges),hex(pc)
        count[0]+=1
    def write(u,access,address,size,value,unused):
        assert (STACK<=address and address+size<=STACK+0x10000
                or DATA+8<=address and address+size<=DATA+10
                or address==CURRENT and size==4
                or address in [0x143cd75,0x143cd76] and size==1),hex(address)
    u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
    cases=[];dispatch_cases=0
    for runtime15 in [0,2]:
        for state,r in enumerate(records):
            for command in range(0x300,0x400):
                u.mem_write(0xf065f8,struct.pack('<I',runtime15))
                u.mem_write(0x143cd75,b'\x55\xaa')
                prepare(u);direct[0]=True
                u.reg_write(R.UC_ARM_REG_R0,r['address']);u.reg_write(R.UC_ARM_REG_R1,command)
                u.emu_start(r['transition'],STOP+4,count=100)
                assert u.reg_read(R.UC_ARM_REG_PC)==STOP
                preserved(u);new=u.reg_read(R.UC_ARM_REG_R0);assert 0<=new<len(records),new
                side_effect=bytes(u.mem_read(0x143cd75,2)).hex()
                # Execute original dispatcher separately: lifecycle is a declared no-op boundary.
                u.mem_write(CURRENT,struct.pack('<I',r['address']))
                obj=bytearray(b'\xa7'*0x20);struct.pack_into('<H',obj,0,command)
                obj[8]=state;obj[9]=0x5a;u.mem_write(DATA,bytes(obj))
                u.mem_write(0x143cd75,b'\x55\xaa');u.mem_write(0x143c689,b'\0')
                prepare(u);direct[0]=False;before=len(callbacks)
                u.reg_write(R.UC_ARM_REG_R0,DATA)
                u.emu_start((BASE+DISPATCH)|1,STOP+4,count=200)
                assert u.reg_read(R.UC_ARM_REG_PC)==STOP
                preserved(u);out=bytes(u.mem_read(DATA,0x20))
                assert out[8]==new and out[9]==state
                assert out[:8]==obj[:8] and out[10:]==obj[10:]
                assert struct.unpack('<I',u.mem_read(CURRENT,4))[0]==records[new]['address']
                assert bytes(u.mem_read(0x143cd75,2)).hex()==side_effect
                expected_callbacks=[]
                if state!=new:
                    if r['leave']: expected_callbacks.append(r['leave']&~1)
                    if records[new]['enter']:expected_callbacks.append(records[new]['enter']&~1)
                assert [int(c['address'],16) for c in callbacks[before:]]==expected_callbacks
                cases.append([runtime15,state,command,new]);dispatch_cases+=1
    # Independently hand-decoded anchors, beyond agreement between original call boundaries.
    def result(state,cmd,runtime15=0):return next(x[3] for x in cases if x[:3]==[runtime15,state,cmd])
    assert [result(0,c) for c in [0x301,0x302,0x320,0x321,0x322,0x325,0x326]]==[0,3,17,9,13,0,2]
    assert [result(1,c) for c in [0x301,0x302,0x325,0x326,0x327]]==[0,3,16,2,10]
    return dict(records=records,case_columns=['declared_runtime_15','old_mode','command','new_mode'],
                cases=cases,direct_transition_cases=len(cases),dispatcher_cases=dispatch_cases,
                original_instructions=count[0],lifecycle_stub_calls=len(callbacks),
                lifecycle_boundary='Original enter/leave callbacks are intercepted as declared no-ops. No real EC mode completion is claimed.',
                interpretation='Object +8 is generated by the EC mode state table, not demonstrated to be a MAIN/monitor stream index.',
                snapshot_copy={'file_offset':'0x665b50','original_memcpy_size':'0xf01',
                               'producer_call':'0x65cc1e','get_ext_info_copy':'0x1c1fc6','size':'0x12d8'},
                sources={'mode_source_string_file':'0x1d5568','string':'EC_Mode.cpp',
                         'dispatcher_file':hex(DISPATCH),'table_va':hex(TABLE),'current_record_va':hex(CURRENT)})


def capture_gate(b):
    def version(extended):
        u=setup(b);u.mem_write(BASE+0x1cb8b8,bytes.fromhex('0d29' if extended else '0c29'))
        stop_kind=[None];count=[0]
        def code(u,pc,size,unused):
            if pc in [BASE+0x1c36d4,BASE+0x1c42fe]:stop_kind[0]=pc;u.emu_stop();return
            if pc==0x9e6684:
                u.reg_write(R.UC_ARM_REG_PC,u.reg_read(R.UC_ARM_REG_LR));return
            assert BASE+0x1c36ae<=pc<BASE+0x1c36d4 or BASE+0x1cb8a8<=pc<BASE+0x1cb934,hex(pc)
            count[0]+=1
        def write(u,access,address,size,value,unused):
            assert STACK<=address and address+size<=STACK+0x10000 or any(
                DATA+0x100+f<=address and address+size<=DATA+0x100+f+4
                for f in [0x794,0x798,0x79c,0x7a0,0x7a4,0x7b0]),hex(address)
        u.hook_add(UC_HOOK_CODE,code);u.hook_add(UC_HOOK_MEM_WRITE,write)
        rows=[]
        for mode in range(256):
            u.mem_write(DATA,struct.pack('<I',PARAM));u.mem_write(DATA+0x100,b'\x5a'*0x1000)
            u.mem_write(DATA+0x108,bytes([mode]))
            for off,v in [(0xba0,12),(0xba4,1),(0xba8,1),(0xbac,0),(0xbb0,0),(0x76c,18)]:
                u.mem_write(PARAM+off,struct.pack('<I',v))
            prepare(u);u.reg_write(R.UC_ARM_REG_R9,DATA);u.reg_write(R.UC_ARM_REG_R11,DATA+0x100)
            u.emu_start((BASE+0x1c36ae)|1,STOP+4,count=300)
            chosen=stop_kind[0]==BASE+0x1c36d4
            assert chosen==(mode in [0,1,2,9,13,16,17])
            fields=[struct.unpack('<I',u.mem_read(DATA+0x100+o,4))[0] for o in [0x794,0x798,0x79c,0x7a0,0x7a4,0x7b0]]
            assert fields==([12 if extended else 0,0,1,1,0,18] if chosen else [0x5a5a5a5a]*6)
            assert u.reg_read(R.UC_ARM_REG_SP)==STACK+0xf000
            assert u.reg_read(R.UC_ARM_REG_R9)==DATA and u.reg_read(R.UC_ARM_REG_R11)==DATA+0x100
            assert all(u.reg_read(getattr(R,f'UC_ARM_REG_R{i}'))==0x77770000+i for i in [4,5,6,7,8,10])
            rows.append(dict(mode=mode,base_look=12,builder_called=chosen,fields=fields))
        return dict(cases=rows,original_instructions=count[0])
    return dict(original=version(False),candidate=version(True),
                scope='Original caller fragment and original builder only; excluded branch is stopped before its unrelated helper. Candidate changes one compare in guest memory.')


def main():
    b=image();records=get_records(b)
    result=dict(status='PASS_ORIGINAL_EC_MODE_AND_CALLER_GATE',cp_sha256=PIN,
                transitions=transitions(b,records),capture_gate=capture_gate(b),
                scope='Declared CPU/memory fixtures only. No live CP, IPC, sensor, ISP, DMA, MAIN recording, monitor pixels or camera flash.')
    (HERE/'ec-mode-results.json').write_text(json.dumps(result,indent=2)+'\n')
    print(result['status'],'mode records',len(records),'transition/dispatcher cases',result['transitions']['direct_transition_cases'])


if __name__=='__main__': main()
