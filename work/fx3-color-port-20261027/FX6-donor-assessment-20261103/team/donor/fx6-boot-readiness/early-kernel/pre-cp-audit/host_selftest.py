#!/usr/bin/env python3
"""No-QEMU parser/guard checks for the owner-only pre-CP stop mode."""
import hashlib
import json
import sys
from pathlib import Path

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent))
from fixed_runner import check_pre_cp,serial_observation

SERIAL=HERE.parent/'runs/fixed-fx3-c72ee0b9/serial.log'
PIN='034552e396f4dbd49aa55e85fb931272d009e41cf7c0a413d85b373b9c7b8536'

def main():
    data=SERIAL.read_bytes()
    if hashlib.sha256(data).hexdigest()!=PIN:raise ValueError('runtime serial changed')
    check_pre_cp()
    base=serial_observation(data)
    if base['first_module_rc']!=0 or base['pre_cp_first_negative_line'] or base['cp_helper_rc_line'] or base['simulation_guard'] or base['ap_guard']:
        raise ValueError('historical boundary misclassified')
    cases={
        'uipc_node_absent':('FX3_UIPC_DEPENDENCY_OR_NODE_NOT_READY\n','pre_cp_first_negative_line'),
        'ldec_insmod_failure':('FX3_LDEC103_INSMOD_RC=1\n','pre_cp_first_negative_line'),
        'ldec_selftest_failure':('FX3_LDEC103_SELFTEST_RC=4\n','pre_cp_first_negative_line'),
        'file_ready_failure':('FX3_FILE103_READY_FAILED before_CP_API_bind=1\n','pre_cp_first_negative_line'),
        'cp_helper_refusal':('FX3_BACKUP_CP_INSMOD_RC=1\n','cp_helper_rc_line'),
        'unexpected_cp_success':('FX3_BACKUP_CP_INSMOD_RC=0\n','cp_helper_rc_line'),
        'pre_ap_guard':('FX3_UTIMER_BEGIN\n','pre_ap_guard'),
    }
    observed={}
    for name,(line,key) in cases.items():
        o=serial_observation(data+line.encode())
        if not o[key]:raise ValueError('missed '+name)
        if name=='unexpected_cp_success' and o['cp_helper_rc']!=0:raise ValueError('positive CP RC misread')
        observed[name]=o[key]
    partial=serial_observation(data+b'FX3_BACKUP_CP_INSMOD_RC=1')
    if partial['cp_helper_rc_line']:raise ValueError('accepted incomplete serial line')
    return {'status':'PASS_HOST_ONLY_NO_QEMU','historical_serial_sha256':PIN,'historical_original_module_rc_zero':True,'synthetic_marker_cases':observed,'incomplete_line_rejected':True,'platform_or_guest_modified':False,'qemu_started':False}

if __name__=='__main__':
    out=main();(HERE/'host-selftest.json').write_text(json.dumps(out,indent=2)+'\n');print(json.dumps({'status':out['status'],'cases':len(out['synthetic_marker_cases'])},indent=2))
