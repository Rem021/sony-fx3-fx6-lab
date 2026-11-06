#!/usr/bin/env python3
"""Independent read-only receipt/command/serial verification for one FX6 run."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
EARLY=HERE.parent
ROOT=HERE.parents[7]
RUN=EARLY/'runs/fixed-fx3-4571c53b'
BASE=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json'
MANIFEST=EARLY/'fixed-kernel-candidate.json'
AUDIT=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/vmopt-20261103-try2-long-media-gap-v2/cpio-audit.json'
PINS={
 'baseline':(BASE,'854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669'),
 'manifest':(MANIFEST,'42cddf844eb37a4712feb59a0c595ab9746eee21b37b210a7f81741bdb16797c'),
 'cpio_audit':(AUDIT,'cc0b3c5b1925aa4bb0cb14aab275f2831833c7378490ca5408789f3824eb4847'),
 'command':(RUN/'command.json','f4a2b1ae34b873d8b02f2d8496325772ef78ea5e7d1cc61eada6921bbd910ecd'),
 'receipt':(RUN/'run-receipt.json','eb3990eb822a57322a496c7819aa47e502f875f0a7f0ca898235a45080164830'),
 'serial':(RUN/'serial.log','dfd0ef290ff0ea0c07335682f3e5a68b0ee5f626d41034a927a7031342df2be8'),
}

def sha_file(path):
    digest=hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda:f.read(4*1024*1024),b''):digest.update(chunk)
    return digest.hexdigest()

def main():
    for key,(path,pin) in PINS.items():
        if sha_file(path)!=pin:raise ValueError('pinned input changed: '+key)
    baseline=json.loads(BASE.read_text());manifest=json.loads(MANIFEST.read_text())
    command=json.loads(PINS['command'][0].read_text());receipt=json.loads(PINS['receipt'][0].read_text())
    if command['manifest_sha256']!=PINS['manifest'][1] or receipt['manifest_sha256']!=PINS['manifest'][1] or command['model_env']!=baseline['model_env'] or manifest['platform_changes'] or manifest['other_firmware_payload_changes']:
        raise ValueError('baseline/manifest/env mismatch')
    original=baseline['fx3_vm_command'].copy();expected=original.copy()
    if len(manifest['firmware_payload_changes'])!=1 or manifest['firmware_payload_changes'][0]['argv_index']!=29:
        raise ValueError('firmware payload changes')
    change=manifest['firmware_payload_changes'][0]
    if original[original.index('-kernel')+1]!=change['from_path'] or original[original.index('-kernel')+1]!=original[29] or command['argv'][29]!=change['to_path']:
        raise ValueError('kernel argv change')
    expected[29]=change['to_path']
    expected[expected.index('-serial')+1]='file:'+str(RUN/'serial.log')
    if command['argv']!=expected:raise ValueError('command differs beyond Image and serial sink')
    files=manifest['unchanged_full_binary_sha256']
    checked={}
    for key in ('qemu_binary','fx3_dtb_full_binary','software_guest_cpio','english_generation4_backup'):
        entry=files[key];path=Path(entry['path'])
        if sha_file(path)!=entry['sha256'] or path.stat().st_size!=entry['bytes']:
            raise ValueError('unchanged platform input '+key)
        checked[key]={'sha256':entry['sha256'],'bytes':entry['bytes']}
    if sha_file(Path(change['to_path']))!=change['to_sha256'] or sha_file(Path(change['from_path']))!=change['from_sha256']:
        raise ValueError('Image identity')
    for name,info in receipt['logs'].items():
        path=RUN/name
        if path.stat().st_size!=info['bytes'] or sha_file(path)!=info['sha256']:
            raise ValueError('runtime log identity '+name)
    serial=PINS['serial'][0].read_text(errors='replace')
    lines=serial.splitlines()
    ordered=[
        'FX3_INSMOD_RC_/kmod/devno.ko=0',
        'FX3_INSMOD_RC_/usr/kmod/osal_utm.ko=0',
        'FX3_INSMOD_RC_/usr/kmod/osal_uipc.ko=0',
        'FX3_UIPC_ORIGINAL_NODE_PRESENT',
        'FX3_LDEC103_INSMOD_RC=0',
        'FX3_LDEC103_GUEST_IOCTL_SELFTEST_PASS three_samples=1 exact32B=1 invalid_lengths_OOB_rejected=1 no_partial_output=1 test_reservation_only=1',
        'FX3_LDEC103_SELFTEST_RC=0',
        'FX3_FILE100_OBSERVER_READY physical=0x41d400000 span=0x300000 native_path=/setting/Backup.bin O_RDONLY=1 no_native_data_writes=1',
        'FX3_FILE100_NATIVE_FILE_READ generation=1 bytes=2229740 fnv64=0x7ba8bcff5c616e29 two_full_reads_equal=1 source_O_RDONLY=1 payload_physical=0x41d401000 unchanged_file_bytes=1',
        'FX3_FILE103_READY_CONFIRMED pid=148 before_CP_API_bind=1',
        'FX3_BACKUP_CP_INSMOD_BEGIN',
        'FX3_BACKUP_CP_INSMOD_RC=7',
        'FX3_BACKUP_CP_OWNER_FAILED',
    ]
    positions=[]
    for marker in ordered:
        indexes=[i for i,line in enumerate(lines) if line==marker]
        if len(indexes)!=1:raise ValueError('missing/duplicate marker '+marker)
        positions.append(indexes[0])
    if positions!=sorted(positions):raise ValueError('guest marker ordering')
    sample_names=('nine-patch-01-1355','panel-02-1228','icon-00-0')
    if any(sum(line.startswith('FX3_LDEC103_GUEST_EXACT sample='+name+' ') for line in lines)!=1 for name in sample_names):
        raise ValueError('LDEC sample evidence incomplete')
    disabled='FX3_SYNC100_DISABLED reason=binding_failure no_success_fallback=1'
    init_fail='initcall init_module+0x0/0x6f0 [fx3_cp_backup_sync100_v4] returned -7'
    if sum(disabled in line for line in lines)!=2 or sum(init_fail in line for line in lines)!=2:
        raise ValueError('CP helper error count')
    if not any('insmod: can\'t insert \'/simulation/fx3-cp-backup-reset-v1.ko\': Argument list too long' in line for line in lines):
        raise ValueError('BusyBox errno text missing')
    if any(marker in serial for marker in ('FX3_AP_NATURAL_BOOTIN_BEGIN','FX3_UTIMER_BEGIN','FX3_BACKUP_INSMOD_RC=')):
        raise ValueError('unexpected later guest progress')
    if receipt['mode']!='pre-cp-first-result' or receipt['reason']!='cp_helper_insmod_rc' or receipt['serial_observation']['cp_helper_rc']!=7 or receipt['qemu_exit']!=0 or receipt['error'] is not None or not receipt['process_reaped'] or not receipt['locks_released']:
        raise ValueError('owner run receipt mismatch')
    if 'u24-002' not in receipt['serial_observation']['linux_version_line'] or not any('nokaslr' in line and 'Kernel command line:' in line for line in lines):
        raise ValueError('FX6 kernel/bootargs marker missing')
    members={v['path']:v for v in json.loads(AUDIT.read_text())['members']}
    if 'system/av-cam.bin' in members:raise ValueError('fixed CPIO now includes AV')
    return {'status':'PASS_INDEPENDENT_RUNTIME_RECEIPT_CHECK','evidence_level':'guest VM serial and host receipt; synthetic CP helper init ran, original FX6 CP core/camera did not','sources':{key:{'path':str(path),'sha256':pin} for key,(path,pin) in PINS.items()},'command_matches_baseline_except_image_and_serial':True,'fixed_platform_inputs':checked,'fx6_image_sha256':change['to_sha256'],'run_elapsed_seconds':receipt['elapsed_seconds'],'guest_marker_line_numbers_1_based':{m:i+1 for m,i in zip(ordered,positions)},'synthetic_ldec_exact_sample_count':len(sample_names),'file100_observer_one_read_seen':True,'cp_disabled_count':2,'cp_init_module_return_minus7_count':2,'busybox_insmod_exit_rc':7,'busybox_errno_text':'Argument list too long','runtime_kallsyms_lookup_address_logged':False,'fx6_ap_av_cp_executed':False,'owner_receipt_pid_reaped_and_locks_released':True,'worker_started_qemu':False}

if __name__=='__main__':
    result=main();(HERE/'verification.json').write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print(json.dumps({'status':result['status'],'cp_init_failures':result['cp_init_module_return_minus7_count'],'worker_started_qemu':False},indent=2))
