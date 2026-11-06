#!/usr/bin/env python3
"""Host-only frozen-platform binding. Never starts QEMU."""
import hashlib,json,plistlib,subprocess,sys
from pathlib import Path
MAC=Path('/Volumes/KAFU2T/AI/Projects/Mac'); TEAM=MAC/'work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team'; CP=TEAM/'donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic'
BASE=MAC/'work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/fx3-platform-frozen-baseline.json'
TARGET=CP/'guest-hybrid-fx6kernel-capid-grmreal46.cpio'; APP=CP/'grm-fbinit/appFw-future-skip.so'; SERIAL=CP/'runs/cp-bind-66ed0f78/serial.log'; REVIEW=TEAM/'fx6-backup-receiver-coordinator-review.json'
BASE_SHA='854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669'; TARGET_SHA='3a08f89d89cfc6db8b12158a0a1147410e42d98713c445c3c38c07eefad8d03b'; APP_SHA='b1fe2274e19d50b6d7ee12886dc233a742358772383f5cf79523de15cf0b55be'; SERIAL_SHA='377142e9dcee7f4f7728db6e9fcb822a9f3e501e61da7f719761d4d506f5050e'; REVIEW_SHA='dd6e157c6873c938b5f90a0c062753f107de2e82e6c00758fd83741a9da049e8'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def verify_artifacts():
    """Rehash baseline/artifact pins WITHOUT pinning a historical serial file."""
    if sha(BASE)!=BASE_SHA:raise RuntimeError('baseline SHA drift')
    d=json.loads(BASE.read_text())
    for name,row in d['sha256'].items():
        p=Path(row['path'])
        if not p.is_file() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise RuntimeError('frozen artifact drift '+str(p))
    if sha(TARGET)!=TARGET_SHA:raise RuntimeError('target CPIO hash drift')
    if sha(APP)!=APP_SHA:raise RuntimeError('APP_ELF hash drift')
    return {'baseline_sha256':sha(BASE),'app_sha256':sha(APP),'target_cpio_sha256':sha(TARGET),'artifacts':len(d['sha256'])}

def main():
 vol=plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))
 if vol.get('VolumeUUID')!='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B':raise SystemExit('UUID mismatch')
 for p,h in [(BASE,BASE_SHA),(TARGET,TARGET_SHA),(APP,APP_SHA),(SERIAL,SERIAL_SHA),(REVIEW,REVIEW_SHA)]:
  if sha(p)!=h:raise SystemExit('input drift '+str(p))
 d=json.loads(BASE.read_text()); arts={}
 for name,row in d['sha256'].items():
  p=Path(row['path']);
  if not p.is_file() or p.stat().st_size!=row['bytes'] or sha(p)!=row['sha256']:raise SystemExit('frozen artifact drift '+str(p))
  arts[name]={'path':str(p),'sha256':row['sha256'],'bytes':row['bytes']}
 args=list(d['fx3_vm_command']);
 if len(args)!=34:raise SystemExit('argv count')
 # Target CPIO is the only argv delta; all platform/kernel/DTB/CPU/memory/model-env stay baseline.
 old=[i for i,a in enumerate(args) if 'guest.cpio' in a]
 if old!=[31]:raise SystemExit('baseline initrd index '+repr(old))
 args[31]='loader,file='+str(TARGET)+',addr=0x440000000,force-raw=on'
 base=d['fx3_vm_command']
 if any(args[i]!=base[i] for i in range(34) if i!=31):raise SystemExit('non-CPIO argv delta')
 required={'-machine':'virt,gic-version=2,secure=off','-cpu':'cortex-a35','-smp':'4','-m':'5120','-accel':'tcg,thread=multi'}
 for k,v in required.items():
  if base[base.index(k)+1]!=v:raise SystemExit('platform parameter '+k)
 plan={'schema':'fx6-backup-observer-baseline-v1','status':'PASS_STATIC_HOST_ONLY_NOT_RUN','baseline_sha256':sha(BASE),'target_cpio':{'path':str(TARGET),'sha256':sha(TARGET),'bytes':TARGET.stat().st_size},'appfw':{'path':str(APP),'sha256':sha(APP)},'serial':{'path':str(SERIAL),'sha256':sha(SERIAL)},'review_sha256':sha(REVIEW),'frozen_artifacts':arts,'qemu_argv_count':34,'qemu_argv':args,'only_delta_index':31,'old_initrd':base[31],'new_initrd':args[31],'fixed_parameters':required,'model_env':d['model_env'],'platform_parameters':d.get('platform_parameters'),'baseline_timestamp_utc':d.get('timestamp_utc'),'note':'host-only binding; no QEMU started; old observer and old authorization not reused'}
 (Path(__file__).resolve().parent.parent/'receipts/baseline-binding.json').write_text(json.dumps(plan,indent=2)+'\n')
 print(json.dumps({'status':plan['status'],'target':sha(TARGET),'app':sha(APP),'only_delta':31,'argv':len(args),'baseline':plan['baseline_sha256']},indent=2))
if __name__=='__main__':main()
