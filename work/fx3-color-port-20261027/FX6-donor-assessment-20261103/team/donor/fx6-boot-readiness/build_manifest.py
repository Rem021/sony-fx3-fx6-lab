#!/usr/bin/env python3
"""Emit a declaration-only candidate manifest; never builds or boots a guest."""
import hashlib
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent


def main():
    receipt=HERE/'preflight-receipt.json'
    data=receipt.read_bytes()
    r=json.loads(data)
    assert r['status']=='PASS_OFFLINE_PRECHECK_ONLY'
    src=r['fixed_sources'];vm=r['vm']
    providers={
        symbol:{'fx3_original_file':file,'fx3_sha256':r['modules']['fx3'][file]['sha256'],'fx6_original_file':file,'fx6_sha256':r['modules']['fx6'][file]['sha256'],'fx3_export_string':r['modules']['fx3'][file]['target_symbols'][symbol]['export_string_present'],'fx6_export_string':r['modules']['fx6'][file]['target_symbols'][symbol]['export_string_present']}
        for symbol,file in [('dma330_mem_transfer_async','kmod/dma330.ko'),('pciatu_map','usr/kmod/pcieatu.ko'),('pciatu_unmap','usr/kmod/pcieatu.ko'),('interchip_transfer_async','usr/kmod/icdt.ko')]
    }
    out={
      'schema':'fx6-boot-readiness-declaration-v1',
      'kind':'OFFLINE_MANIFEST_ONLY_NOT_A_BOOTABLE_CANDIDATE',
      'preflight_receipt_sha256':hashlib.sha256(data).hexdigest(),
      'current_fx3_vm_baseline':{'candidate_path':src['candidate']['path'],'candidate_sha256':src['candidate']['sha256'],'cpio_sha256':src['guest_cpio']['sha256'],'qemu_machine':vm['qemu_machine_args'],'memory_mib':vm['qemu_memory_mib'],'smp':vm['qemu_smp']},
      'routes':{
        'fx6_own_firmware_on_virt':{
          'not_started':True,'first_gate':'FX6 ARM64 Image + adapted virt DTB + minimal console init reach serial; native FX6 cxd90057 DTB is not virt guest DTB',
          'inputs':{k:src[k] for k in ('fx6_kernel','fx6_updater_boot_dtb','fx6_application_setting_dtb','fx6_system_partition','fx6_cp_partition','fx6_usr_partition','fx6_av','fx6_cp')},
          'native_mounts':r['fx6_fstab_mounts'],
          'defer_until_first_gate_passes':['/dev/nflasha partition mounts and writable settings are not provided by the current CPIO','Sony DMA/PCIe/CP/AV device models and their MMIO/interrupt behavior','full AP and movie control path'],
          'single_gate_resources':{'reuse_existing_qemu':'virt,gic-version=2,secure=off','vcpus':4,'memory_mib':5120,'wallclock_limit_seconds':180,'new_device_count':0,'VM_owner_only':True,'output':'serial log, QEMU exit, original kernel/DTB/CPIO SHA; no AP or camera claim'}
        },
        'fx6_function_on_fx3_firmware':{
          'first_gate':'Establish original FX3 LIRO and FX3 AV baseline before considering FX6 AV substitution',
          'current_blockers':['CPIO contains liro.ko but no system/av-cam.bin','native insmod_drv2 names eight modules absent from current CPIO, including pciedma.ko; whether each is required for this reduced guest is unresolved','custom init does not explicitly load dma330.ko, pcieatu.ko or icdt.ko','TRY2 serial records LIRO unresolved dma330_mem_transfer_async, pciatu_map, pciatu_unmap, interchip_transfer_async'],
          'fx3_original_av':src['fx3_av'],'fx6_donor_av_for_later_only':src['fx6_av'],'provider_edges':providers,
          'single_gate_experiment_for_vm_owner':{
             'start':'from pinned FX3 candidate in a new isolated candidate artifact, after current black-frame work yields runtime; do not modify current candidate',
             'preconditions':['resolve recursive import/export edges of each module actually proposed for loading; distinguish kernel exports from optional native insmod steps','audit original FX3 provider module init and hardware access against existing virt DTB/MMIO','never stub export return values or claim link success is a working hardware model'],
             'proposed_guest_delta':['stage original FX3 system/av-cam.bin at /system/av-cam.bin with its SHA','stage any pin-verified missing original FX3 modules that the selected dependency closure proves necessary','load selected original FX3 prerequisite modules in native relative order under fail-fast RC checks; retain original Backup and IM'],
             'read_only_observables':['per-module insmod RC and /proc/modules export presence','LIRO load RC and all unresolved symbols','ORIL header +0x20 and provider slots only after actual load','first AV map/entry PC or first fault with serial/QMP provenance'],
             'stop_rule':'stop at first original module init, symbol resolution, file-open or ORIL load failure; no synthetic success reply',
             'resources':{'vcpus':4,'memory_mib':5120,'wallclock_limit_seconds':650,'reason':'pinned TRY2 LIRO unresolved symbol event at about guest 501.9 s','new_device_count':0,'VM_owner_only':True,'estimated_new_candidate_cpio_bytes':'existing 432 MiB plus one original AV image about 13 MiB; no full donor clone'}
          },
          'later_gates':['bind actual FX3 Backup current byte and event route','test FX6 AV ABI/model differences only after FX3 baseline loads','CP/DMA/pixel or RAW acceptance remains open']
        }
      },
      'not_performed':['QEMU/VM start','VM lock acquisition','CP execution','AV execution','device/USB/SD/camera access','firmware publication']
    }
    print(json.dumps(out,indent=2,ensure_ascii=False))


if __name__=='__main__':main()
