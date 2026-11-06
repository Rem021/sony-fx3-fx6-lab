#!/usr/bin/env python3
"""Pin the runtime owner's FX3 platform and declare FX6 Image-only substitution."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
ROOT=HERE.parents[6]
BASE=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json'
BASE_SHA='854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669'
COMMAND=ROOT/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/runs/try2gapinternal-47e2924a/command.json'
FX6=HERE.parents[1]/'fat-files/nflasha3/vmlinux.bin'
FX6_SHA='bc4925e701ae363c797f22ef28f29dc48fd17af7f25a3f64d7d0824312c0dab9'


def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda:f.read(4*1024*1024),b''):h.update(block)
    return h.hexdigest()


def main():
    if sha(BASE)!=BASE_SHA:raise ValueError('runtime owner FX3 baseline changed')
    b=json.loads(BASE.read_text())
    if sha(COMMAND)!=b['source_run_command_sha256']:raise ValueError('historical command changed')
    original=json.loads(COMMAND.read_text())
    if original['args']!=b['fx3_vm_command'] or original['model_env']!=b['model_env']:
        raise ValueError('baseline command/env does not match historical run')
    for item in b['sha256'].values():
        p=Path(item['path'])
        if not p.is_file() or p.is_symlink() or p.stat().st_size!=item['bytes'] or sha(p)!=item['sha256']:
            raise ValueError('fixed platform input mismatch: '+str(p))
    if sha(FX6)!=FX6_SHA:raise ValueError('FX6 Image changed')
    prior=json.loads((HERE/'candidate.json').read_text())
    if prior['status']!='WITHDRAWN_DO_NOT_RUN_FIXED_FX3_PLATFORM_CONSTRAINT':raise ValueError('exploratory candidate not marked withdrawn')
    args=b['fx3_vm_command'].copy()
    kernel_at=args.index('-kernel')+1
    previous=args[kernel_at]
    args[kernel_at]=str(FX6)
    expected=b['fx3_vm_command'].copy();expected[kernel_at]=str(FX6)
    if args!=expected:raise ValueError('unexpected platform diff')
    return {
      'schema':'fx6-image-only-on-frozen-fx3-platform-v1','status':'OFFLINE_PINNED_NOT_EXECUTED',
      'owner_baseline':{'path':str(BASE),'sha256':BASE_SHA},
      'source_run_command_sha256':b['source_run_command_sha256'],
      'fx3_platform':b['platform_parameters'],'model_env':b['model_env'],
      'unchanged_full_binary_sha256':{k:b['sha256'][k] for k in ('qemu_binary','fx3_dtb_full_binary','software_guest_cpio','english_generation4_backup')},
      'firmware_payload_changes':[{'argv_index':kernel_at,'role':'kernel Image','from_path':previous,'from_sha256':b['sha256']['fx3_kernel']['sha256'],'to_path':str(FX6),'to_sha256':FX6_SHA}],
      'candidate_argv_before_observer_serial_retarget':args,
      'platform_changes':[],
      'other_firmware_payload_changes':[],
      'withdrawn_exploratory_candidate':{'path':str(HERE/'candidate.json'),'status':prior['status'],'new_initrd_sha256':prior['initrd']['sha256'],'new_dtb_sha256':prior['dtb']['sha256'],'reason':'altered initrd contents and DTB chosen bootargs/initrd-end; conflicts with fixed FX3 platform directive'},
      'stop_at_first_kernel_serial_marker':'Linux version ',
      'guard_before_AP_marker':'FX3_AP_NATURAL_BOOTIN_BEGIN',
      'maximum_wall_seconds':180,
      'boot_result':'UNTESTED',
      'what_this_does_not_test':['FX6 AP','FX6 AV','FX6 CP','movie color','RAW','camera or storage hardware'],
    }


if __name__=='__main__':
    out=main();(HERE/'fixed-kernel-candidate.json').write_text(json.dumps(out,indent=2,ensure_ascii=False)+'\n');print(json.dumps(out,indent=2,ensure_ascii=False))
