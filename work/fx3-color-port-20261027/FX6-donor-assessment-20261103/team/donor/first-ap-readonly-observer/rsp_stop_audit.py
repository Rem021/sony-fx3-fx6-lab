#!/usr/bin/env python3
"""Host-only postmortem of the one authorized second window, no QEMU calls."""
import json
from pathlib import Path
from readonly_probe import sha
HERE=Path(__file__).resolve().parent
RUN=HERE/'runs/ap-ro-c714785a'
QEMU=HERE.parents[5]/'work/fx3-vm-20261101/menu-repair-01/runtime/qemu-display-build/sources/qemu-11.1.2/gdbstub'
PINS={
    RUN/'serial.log':'564eb0c28480197ca28d0b0031d1dbe6b93a05a855f8a9093d60ba62a69959c9',
    RUN/'receipt.json':'2149e6305235b35b50253197ebb99d815ddaa508681430cbad455fb52f477085',
    RUN/'readonly-observation.json':'0ad41b3b374060c59918ad9db5d534297096b9491a0949ff7c276d04afc261b3',
    RUN/'observer-run_once.py':'928306a009abaaf596cd4f90fa515e66f991a8b41620ab1906ba8966554068e4',
    RUN/'observer-readonly_probe.py':'fec9ce951a078522b73766dbc7e0390563a5d1a581d9caa451b7c92de87b2a0c',
    RUN/'observer-two_phase_identity.py':'d164c95a14e0d906083e6bbbd05facb4827cc1d4a59dbfc784830ebc2cd6de68',
    QEMU/'system.c':'196af474a5aacefab3394162b10537efcf9dbd55e2ec2fa291a0cbd71877352f',
    QEMU/'gdbstub.c':'a03d5b7aa6a2188f4eebda464a6e6d7914dacfb0898136323c5c857c829cba6a',
}
def main():
    assert all(sha(p)==h for p,h in PINS.items())
    receipt=json.loads((RUN/'receipt.json').read_text())
    obs=json.loads((RUN/'readonly-observation.json').read_text())
    b=(RUN/'serial.log').read_bytes()
    request=b.find(b'FX3_PROVIDER_REQUEST destination=0x92840747')
    assertion=b.find(b'assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075')
    assert 0<request<assertion and receipt['stop']=='observation_budget_end'
    assert obs['records']==[] and obs['stage']=='await_audio_entry;cleanup'
    assert receipt['breakpoint_cleanup']['attempted'] and receipt['breakpoint_cleanup']['all_removed']
    assert receipt['cleanup']['API16_restored'] and receipt['qemu_reaped'] and receipt['qemu_exit']==0
    stub=(QEMU/'gdbstub.c').read_text();system=(QEMU/'system.c').read_text()
    frozen=(RUN/'observer-run_once.py').read_text()
    allow='gdbserver_state.allow_stop_reply = cmd->allow_stop_reply;'
    gate='if (!gdbserver_state.allow_stop_reply) {'
    assert allow in stub and gate in system
    assert '.handler = handle_continue' in stub and '.handler = handle_v_cont' in stub
    assert '.allow_stop_reply = true' in stub
    assert 'self.qmp.call(\'cont\')' in frozen and 'self.rsp.command(\'vCont;c\')' not in frozen
    out={
      'status':'HOST_ONLY_GDB_STOP_REPLY_GATE_IDENTIFIED_RUNTIME_HIT_UNPROVEN',
      'inputs_sha256':{str(p):h for p,h in PINS.items()},
      'run':str(RUN),'run_stop':receipt['stop'],'elapsed_seconds':receipt['elapsed_seconds'],
      'z1_inserted_address':obs['mapping']['cap']['bias']+0x1e730,
      'z1_removed_reply':receipt['breakpoint_cleanup']['results'][0]['reply'],
      'rsp_hit_records':len(obs['records']),'qmp_debug_state_before_cleanup':'not_recorded',
      'serial_request_byte_offset':request,'serial_assert_byte_offset':assertion,
      'cap_current_CPU_ELF_PHD_code':'not_read','cap_model_initialized':'not_read',
      'cap_owner':'not_read','AP_w0':'not_read',
      'source_gate':{
        'gdbstub_c_approx_lines':'997 run_cmd_parser copies allow_stop_reply; 2080/2091 c/C, 1476 vCont permit stop reply; 2336 gdb_read_byte initially clears it',
        'system_c_approx_lines':'144 returns without packet if flag false; 211 emits T...thread only when allowed',
        'frozen_runner':'Probe.arm and between hits use QMP cont; no GDB continue command'},
      'inference':'A T packet cannot be expected after QMP-only cont with allow_stop_reply false; installed Z1 and serial stall are not a recorded breakpoint hit.',
      'cleanup':{'api16_restored':receipt['cleanup']['API16_restored'],
                 'original_api16_hex':receipt['cleanup']['restore']['attempts'][-1]['api16_hex'],
                 'qemu_exit':receipt['qemu_exit'],'qemu_reaped':receipt['qemu_reaped'],
                 'inputs_unchanged':receipt['inputs_unchanged'],'locks':receipt['locks']},
      'next_host_only_fix':'Use a bounded GDB resume packet after Z1 to set allow_stop_reply, with explicit ACK/async T05 handling and QMP debug cross-check; no guest writes. Requires separate review and VM authorization.'}
    (HERE/'rsp-stop-audit.json').write_text(json.dumps(out,indent=2)+'\n')
    print(json.dumps({'status':out['status'],'records':0,'request':request,'assert':assertion}))
if __name__=='__main__':main()
