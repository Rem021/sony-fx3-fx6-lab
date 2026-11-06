#!/usr/bin/env python3
import hashlib,json
from collections import Counter
from pathlib import Path
C=Path(__file__).resolve().parent.parent; OUT=C/'receipts'; W=C/'work'; OLD=Path('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/parallel-review-20261105/fx6-backup-read-contract/work')
def h(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def main():
 win=json.loads((OUT/'uipc-3e014d-windows.json').read_text()); sends=win['sends']; passes=win['passes']; windows=win['windows']
 tid=Counter(x['tid'] for x in sends); op=Counter(x['op'] for x in sends); heads=Counter(x['body_head'] for x in passes if x.get('body_head'))
 edges=[
  {'edge':'appFw Backup_nread UND -> libbackup.Backup_nread','evidence':'appFw dynsym *UND*; libbackup defines VMA 0x24b0; im/bootin DT_NEEDED libbackup; appFw DT_NEEDED lacks libbackup','confidence':'static provider candidate; global loader binding not runtime-captured'},
  {'edge':'libbackup.Backup_nread -> backup_sync_msg','evidence':'0x24e4 bl backup_sync_msg@plt; w1=0x3e014d,w2=0x1f,w3=3; 0x24b0..0x24f4','confidence':'high static'},
  {'edge':'libbackup.backup_sync_msg -> osal_snd_sync_msg','evidence':'0x1a10; calls osal_valloc_msg_wait/osal_snd_sync_msg/osal_free_msg; target 0x3e014d','confidence':'high static'},
  {'edge':'osal_snd_sync_msg -> __osal_snd_sync_msg -> u_osal_snd_sync_msg -> ioctl(0xffffffff80000005)','evidence':'libosal_uipc 0x6458 -> 0x61e8; target bit15=0 -> 0x6390; u_osal 0x3a98; ioctl x1=0xffffffff80000005, fd from /dev/uipc; serial FX3_IOCTL_PASS fd=3 request=0xffffffff80000005 and FX3_UIPC_PASS','confidence':'high static+serial'},
  {'edge':'ioctl -> kernel/user UIPC receiver for 0x3e014d','evidence':'missing: no osal_reg_*_cb(0x3e014d) binding or kernel dispatch found; UIPC_PASS only shows proxy','confidence':'open'}]
 candidates={
  'backup.ko':{'sha256':h(OLD/'backup.ko'),'facts':'Backup_nread 0x1eb8/inner 0x760; backup_async_recv 0x7500 uses 0x3e0811; backup_sync_msg 0x40e8 is sender/OSAL client; no 0x3e014d address construction in 129 .ko scan','receiver_claim':False},
  'fx3-cp-backup-reset-v1.ko':{'sha256':h(W/'fx3-cp-backup-reset-v1.ko'),'facts':'source fx6-cp-backup-sync100-agnostic; handles 0x903e0811/op30 and backupfile callbacks; no 0x3e014d construction; not receiver','receiver_claim':False},
  'libbkdmn.so':{'sha256':h(W/'libbkdmn.so'),'facts':'BkDmn_Manager 0x2c30 receives queue 0x82cd08e0; BkDmn_reg_sid sends 0x82cd08e0; imports Backup_write/sync, not Backup_nread; not 0x3e014d receiver','receiver_claim':False},
  'libbackup.Backup_reg_cb':{'facts':'0x1890 registers osal_reg_msg_queue_cb with 0x3e414e (async callback), not 0x3e014d; PLT relocation 0x13080','receiver_claim':False},
  'libInfraExtBackupCommunicator':{'facts':'registers osal_reg_sync_msg_queue_cb for external backup; imports Backup_read, no nread; not mapped to 0x3e014d','receiver_claim':False}}
 app_sends=[x for x in sends if x['tid']=='375']; late=[x for x in sends if x['tid'] in ('375','506')]
 value={'schema':'fx6-receiver-trace-v1','serial':{'sha256':h('/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/runs/cp-bind-66ed0f78/serial.log'),'passes':len(passes),'sends':len(sends),'windows':len(windows),'send_tid_counts':dict(tid),'send_op_counts':dict(op),'body_head_top':heads.most_common(8),'early_1302_1307':{'lines':'1302/1303/1305/1307','tid':'227','name':'bootin.elf','op':'10/5/11','body_head':'030000000000000002000000c1ffffff','use':'early bootin UIPC; NOT appFw key request'},'appfw_11783':{'line':11783,'tid':'375','name':'AppFw','op':'5','tag1':'0x20','body_head':'no paired body in immediate window','after_asserts':'after 11686/11736 model asserts','use':'only one appFw 0x3e014d send; no key/return visible; cannot associate two keys'},'late_506':[{'line':x['line'],'tid':x['tid'],'tag1':x['tag1']} for x in late if x['tid']=='506']},
  'known_edges':edges,'receiver_candidates':candidates,'provider_closed':False,'missing_binding':['osal_reg_msg_queue_cb / osal_reg_sync_msg_queue_cb registration for 0x3e014d (callback address)','kernel UIPC dispatch table entry/target queue for 0x3e014d','request body containing key 0x02cf0214/0x02cf0218 and paired response/return','runtime trace of appFw Backup_nread argument/callback'],'data_origin_conclusion':'No evidence that the two appFw key reads (0x02cf0214/0x02cf0218) reached kernel Backup_nread/inner 0x760; existing Backup 92fe remains a candidate input, not proven appFw source. The receiver of 0x3e014d is not identified, so data/return origin cannot be determined.'}
 (OUT/'receiver-trace.json').write_text(json.dumps(value,indent=2)+'\n')
 print(json.dumps({'passes':len(passes),'sends':len(sends),'windows':len(windows),'tid':dict(tid),'op':dict(op),'heads':heads.most_common(5),'provider_closed':False,'missing':value['missing_binding'],'conclusion':value['data_origin_conclusion'],'receipt':str(OUT/'receiver-trace.json')},indent=2))
if __name__=='__main__':main()
