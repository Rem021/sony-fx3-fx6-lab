#!/usr/bin/env python3
"""Read-only user provider/preload/kernel-dispatch audit (target CPIO members)."""
import hashlib,json,subprocess
from pathlib import Path
C=Path(__file__).resolve().parent.parent; W=C/'work'; OUT=C/'receipts'; OD='/Applications/Xcode.app/Contents/Developer/Toolchains/XcodeDefault.xctoolchain/usr/bin/llvm-objdump'
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def dump(args):
 return subprocess.run([OD]+args+[str(W/'libbackup.so')],capture_output=True,text=True).stdout
def dyn(path):return subprocess.run([OD,'-p',str(path)],capture_output=True,text=True).stdout
def syms(path):return subprocess.run([OD,'-T',str(path)],capture_output=True,text=True).stdout
def needed(path):return [l.split()[-1] for l in dyn(path).splitlines() if l.strip().startswith('NEEDED')]
def defined_or_undef(path,names):
 s=syms(path); out={}
 for n in names:
  rows=[l for l in s.splitlines() if l.rstrip().endswith(n)]
  out[n]=rows[0].strip() if rows else None
 return out
def main():
 app=W/'appFw.so'; im=W/'im.elf'; boot=W/'bootin.elf'; lb=W/'libbackup.so'; up=W/'libosal_uipc.so'; ko=W/'backup.ko'
 preloads={'fx3-backup-return-v1.so':W/'fx3-backup-return-v1.so','ioctl-trace.so':W/'ioctl-trace.so','fx3-icrypt-observe-v1.so':W/'fx3-icrypt-observe-v1.so'}
 value={'schema':'fx6-user-provider-chain-v1','appFw':{'sha256':h(app),'needed':needed(app),'backup_nread':defined_or_undef(app,['Backup_nread'])['Backup_nread']},
  'hosts':{'im.elf':{'sha256':h(im),'needed':needed(im)},'bootin.elf':{'sha256':h(boot),'needed':needed(boot)}},
  'libbackup':{'path':'usr/lib/libbackup.so','sha256':h(lb),'needed':needed(lb),'symbols':defined_or_undef(lb,['Backup_nread','backup_sync_msg','osal_snd_sync_msg','osal_valloc_msg_wait','osal_free_msg']),
   'backup_nread_vma':'0x24b0','backup_sync_msg_vma':'0x1a10','wrapper_observed':'Backup_nread writes key/capacity/buffer and calls backup_sync_msg with w1=0x3e014d,w2=0x1f,w3=3; return status in [x29+0x1c]'},
  'transport':{'libosal_uipc':{'sha256':h(up),'symbols':defined_or_undef(up,['osal_snd_sync_msg','osal_valloc_msg_wait','osal_free_msg','osal_snd_msg']),'needed':needed(up)},
   'path':'libbackup.backup_sync_msg -> osal_valloc_msg_wait/osal_snd_sync_msg/osal_free_msg; libosal_uipc exports osal_snd_sync_msg; libbackup does not NEEDED libosal but im/bootin DO => global-scope resolution candidate; exact loader binding not captured'},
  'preloads':{},'kernel':{'path':'usr/kmod/backup.ko','sha256':h(ko),'Backup_nread_vma':'0x1eb8','inner_vma':'0x760','backup_sync_msg_vma':'0x40e8','backup_async_recv_vma':'0x7500','observation':'kernel backup_async_recv uses UIPC msg 0x3e0811; user backup_sync_msg uses 0x3e014d; no receiver mapping for 0x3e014d to Backup_nread located in this bounded audit'},'provider_closed':False,
  'unknown_jump':['user libbackup Backup_nread -> backup_sync_msg -> osal_snd_sync_msg(0x3e014d) endpoint','which kernel/user handler receives 0x3e014d and whether it calls kernel Backup_nread/inner 0x760','whether libosal_uipc ioctl/read path or ioctl-trace interposition is used','actual runtime binding of libbackup in appFw global scope'],
  'conclusion':'libbackup is the user provider of Backup_nread and im/bootin load it; preloads do not define Backup_nread. The user->kernel inner dispatch is not closed, so do not claim appFw actually reaches the reviewed kernel helper.'}
 for n,p in preloads.items():
  s=syms(p); defs={q for q in ('Backup_nread','backup_sync_msg','ioctl','open','read','write','dlopen') if any(q in l and ' g ' in l for l in s.splitlines())}
  value['preloads'][n]={'sha256':h(p),'defines_relevant':sorted(defs),'needed':needed(p)}
 (OUT/'provider-chain.json').write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'appFw_needed':value['appFw']['needed'],'appFw_nread':value['appFw']['backup_nread'],'im_needed':value['hosts']['im.elf']['needed'],'boot_needed':value['hosts']['bootin.elf']['needed'],'libbackup':value['libbackup'],'transport':value['transport'],'preloads':value['preloads'],'kernel':value['kernel'],'provider_closed':False,'receipt':str(OUT/'provider-chain.json')},indent=2))
if __name__=='__main__':main()
