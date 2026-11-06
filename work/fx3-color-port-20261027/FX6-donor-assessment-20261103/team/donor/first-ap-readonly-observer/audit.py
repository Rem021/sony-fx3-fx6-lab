#!/usr/bin/env python3
"""Offline, no-QEMU input/contract audit for the read-only AP observer."""
import json
import sys
from pathlib import Path
HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE))
from readonly_probe import sha, choose_mapping, elf_loads, AP_WORD, CAP_WORD
import run_once as observer

def main():
    pins={
        observer.PARENT/'run_ap_once.py':observer.PARENT_SHA,
        observer.AP_ELF:observer.AP_SHA,
        observer.CAP_ELF:observer.CAP_SHA,
        observer.HISTORICAL:observer.HIST_SHA,
        observer.FX3_RUNTIME/'gdb_sysregs104_v2.py':observer.SYSREG_SHA,
    }
    qsrc=observer.FX3_RUNTIME/'qemu-display-build/sources/qemu-11.1.2'
    pins.update({
        qsrc/'accel/tcg/tcg-accel-ops.c':'79a918acaf0e6c770b2095036c06c513a567beb478a3aed113edb738d00151a2',
        qsrc/'gdbstub/system.c':'196af474a5aacefab3394162b10537efcf9dbd55e2ec2fa291a0cbd71877352f',
        qsrc/'gdbstub/gdbstub.c':'a03d5b7aa6a2188f4eebda464a6e6d7914dacfb0898136323c5c857c829cba6a',
    })
    got={str(p):sha(p) for p in pins}
    assert all(got[str(p)]==h for p,h in pins.items())
    # These source assertions make the local current-version support claim
    # reproducible without treating the web documentation as runtime evidence.
    tcg=(qsrc/'accel/tcg/tcg-accel-ops.c').read_text()
    system=(qsrc/'gdbstub/system.c').read_text()
    stub=(qsrc/'gdbstub/gdbstub.c').read_text()
    assert 'case GDB_BREAKPOINT_HW:' in tcg and 'cpu_breakpoint_insert(cpu, addr, BP_GDB, NULL)' in tcg
    assert 'cpu_breakpoint_remove(cpu, addr, BP_GDB)' in tcg
    assert 'g_string_printf(buf, "T%02xthread:%s;", ret, tid->str)' in system
    assert 'vm_stop(RUN_STATE_DEBUG)' in system
    assert 'gdb_breakpoint_remove_all(gdbserver_state.c_cpu)' in stub
    assert 'gdbserver_state.allow_stop_reply = cmd->allow_stop_reply;' in stub
    assert '.handler = handle_continue,' in stub and '.allow_stop_reply = true,' in stub
    assert 'void gdb_read_byte(uint8_t ch)' in stub and 'if (runstate_is_running()) {' in stub
    assert 'if (!gdbserver_state.allow_stop_reply)' in system
    assert 'void gdb_continue(void)' in system and 'vm_start();' in system
    baseline,structure=observer.frozen.verify()
    base=baseline['fx3_vm_command'];modified=list(base)
    modified[20]='file:<new-run>/serial.log'
    modified[31]='loader,file='+str(observer.PARENT/'guest-three-entry.cpio')+',addr=0x440000000,force-raw=on'
    diffs=[i for i,(a,b) in enumerate(zip(base,modified)) if a!=b]
    assert len(base)==34 and diffs==[20,31]
    assert base[base.index('-qmp')+1]=='unix:q,server=on,wait=off'
    assert base[base.index('-gdb')+1]=='chardev:keygate93'
    assert base[base.index('-smp')+1]=='4'
    assert base[base.index('-machine')+1]=='virt,gic-version=2,secure=off'
    mapping=choose_mapping(observer.HISTORICAL.read_bytes(),observer.AP_ELF,observer.CAP_ELF)
    assert mapping and mapping['block_complete'] and mapping['pid']==239
    assert mapping['ap']['bias']==0x7edd55b000 and mapping['cap']['bias']==0x7f90b0c000
    instruction_files={}
    for name,path,words in [('ap',observer.AP_ELF,AP_WORD),('cap',observer.CAP_ELF,CAP_WORD)]:
        loads=elf_loads(path);located={}
        with path.open('rb') as f:
            for va,expected in words.items():
                matches=[x for x in loads if x['va']<=va and va+4<=x['va']+x['filesz']]
                assert len(matches)==1,(name,hex(va))
                fileoff=matches[0]['fileoff']+va-matches[0]['va']
                f.seek(fileoff);actual=f.read(4).hex()
                assert actual==expected,(name,hex(va),actual,expected)
                located[hex(va)]={'file_offset':hex(fileoff),'original_le_word':actual}
        instruction_files[name]=located
    tests=json.loads((HERE/'host-tests.json').read_text())
    assert tests['status']=='PASS_NO_QEMU' and len(tests['cases'])>=9
    assert tests['runner_sha256']==sha(HERE/'run_once.py') and tests['observer_sha256']==sha(HERE/'readonly_probe.py')
    assert tests['identity_sha256']==sha(HERE/'two_phase_identity.py')==observer.IDENTITY_SHA
    out={
        'status':'PASS_STATIC_HOST_ONLY_NOT_RUN',
        'input_sha256':got,
        'scripts_sha256':{p.name:sha(p) for p in [HERE/'run_once.py',HERE/'readonly_probe.py',
                                                HERE/'two_phase_identity.py',HERE/'test_host.py',HERE/'audit.py']},
        'frozen_cpio_sha256':observer.frozen.PINS['candidate'],
        'frozen_argv_count':34,'frozen_argv_changed_indices':[20,31],
        'frozen_argv_delta':{'20_serial':'new private run/serial.log',
            '31_initrd':'same pinned three-entry CPIO with same addr 0x440000000 and force-raw'},
        'qmp_socket':'q','gdb_socket':'g','smp':4,
        'rsp_resume_contract':'addressless c: immediate transport ACK only; subsequent T05 stop requires QMP debug; no RSP byte while guest running',
        'historical_map':{'pid':mapping['pid'],'ap_bias':hex(mapping['ap']['bias']),
            'cap_bias':hex(mapping['cap']['bias']),
            'ap_branch_pc':hex(mapping['ap']['bias']+0x20ef7a0),
            'cap_audio_pc':hex(mapping['cap']['bias']+0x1e730),
            'caveat':'historical ASLR example only; live map must be recalculated'},
        'original_instruction_words':{'ap':{hex(k):v for k,v in AP_WORD.items()},
                                      'cap':{hex(k):v for k,v in CAP_WORD.items()}},
        'original_instruction_file_offsets':instruction_files,
        'host_tests':tests,
        'runtime_evidence':'none_this_turn',
    }
    (HERE/'audit.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':out['status'],'changed_indices':diffs,'cases':len(tests['cases'])}))

if __name__=='__main__':main()
