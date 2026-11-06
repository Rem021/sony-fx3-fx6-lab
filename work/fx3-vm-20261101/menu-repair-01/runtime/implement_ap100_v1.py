from pathlib import Path
import json,plistlib,subprocess,hashlib
R=Path(__file__).resolve().parent; H=R/'helpers'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
def put(n,s):
 p=H/n; assert not p.exists(),p; p.write_text(s)
s=(H/'fx3-cp-backup-reset-core-v1.h').read_text().replace('rd32(b+8)!=0','(b[8]!=0||b[9]>1||b[10]!=0||b[11]!=0)')
put('fx3-cp-backup-reset-core-v2-sync100.h',s)
s=(H/'fx3-capid-v48-panel97.c').read_text()
insert='''
/* AP100 exact ON1 software configuration. Requests remain original-caller owned. */
static struct {unsigned on,pending;unsigned long generation;} touch100;
static struct {void *request;unsigned source;long tid;unsigned long generation,transaction;} touch100_live[8];
static int touch100_dispatch(void *request){
 const unsigned char exact[10]={13,32,70,1,10,0,1,128,1,0};
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;
 if(msg_size(request)!=10||memcmp(request,exact,10))return -1024;
 unsigned from=source(request);if(!local(from))return -1024;int slot=-1;
 for(int i=0;i<8;i++){if(touch100_live[i].request==request||(touch100_live[i].request&&touch100_live[i].source==from))return -1021;if(!live[i].p&&slot<0)slot=i;}
 if(slot<0||serial==~0UL||touch100.generation==~0UL)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);
 if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&live[i].p==reply){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 const unsigned char answer[12]={13,32,70,17,12,0,1,128,0,0,89,0};memcpy(reply,answer,12);set_source(reply,0x92840747);
 unsigned long generation=touch100.generation+1,transaction=serial+1;
 live[slot].p=reply;live[slot].dst=from;live[slot].command=0x146;live[slot].serial=++serial;
 touch100_live[slot].request=request;touch100_live[slot].source=from;touch100_live[slot].tid=syscall(178);touch100_live[slot].generation=generation;touch100_live[slot].transaction=transaction;
 rc=send_msg(from,reply);
 if(rc){memset(touch100_live+slot,0,sizeof touch100_live[slot]);memset(live+slot,0,sizeof live[slot]);if(release(from,reply))fault=1;dprintf(2,"FX3_TOUCH100_ROLLBACK generation=%lu result=%d state_unchanged=1 request_caller_owned=1\\n",generation,rc);return rc;}
 touch100.on=touch100.pending=1;touch100.generation=generation;
 dprintf(2,"FX3_TOUCH100_COMMIT request=0d2046010a0001800100 reply=0d2046110c00018000005900 source=%#x lease=%lu generation=%lu pending_hardware=1 physical_touch_verified=0 request_caller_owned=1\\n",from,transaction,generation);return 0;
}
'''
s=s.replace('\nint osal_snd_msg(unsigned int dst,void *request){',insert+'\nint osal_snd_msg(unsigned int dst,void *request){')
a=' const char *ud=getenv("FX3_SYS_UUD");'
s=s.replace(a,''' const char *touch=getenv("FX3_TOUCH_PANEL");if(enabled&&request&&touch&&!strcmp(touch,"headless_touch_config")&&dst==0x92840747&&msg_size(request)>=4&&pg_get(request)==0x0146200d){enter();int out=touch100_dispatch(request);leave();if(out)dprintf(2,"FX3_TOUCH100_REJECT result=%d no_reply=1\\n",out);*__errno_location()=saved;return out;}
'''+a)
a=' int rc=live[found].dst==dst?release(dst,p):-1021;'
s=s.replace(a,''' if(touch100_live[found].request&&(touch100_live[found].tid!=syscall(178)||touch100_live[found].source!=dst||touch100_live[found].transaction!=live[found].serial||!touch100_live[found].generation||touch100_live[found].generation>touch100.generation)){leave();*__errno_location()=saved;return -1021;}
'''+a)
s=s.replace('if(rc)fault=1;else {if(sys_uud_kind[found])','if(rc)fault=1;else {if(touch100_live[found].request){dprintf(2,"FX3_TOUCH100_CONSUMED source=%#x generation=%lu transaction=%lu native_free_result=0 pending_hardware=1\\n",dst,touch100_live[found].generation,touch100_live[found].transaction);memset(touch100_live+found,0,sizeof touch100_live[found]);}if(sys_uud_kind[found])')
put('fx3-capid-v49-touch100.c',s)
# Existing owner remains unique; retain CP99 and CP88 reset implementation.
s=(H/'fx3-cp-backup-reset-v3-date99.c').read_text().replace('fx3-cp-backup-reset-core-v1.h','fx3-cp-backup-reset-core-v2-sync100.h')
s=s.replace('static int cp_reset_send_backup99(', 'static int cp_reset_send_backup100_prior(')
s=s.replace('static const struct{int(*send)', '#include "fx3-backup-sync100-v1.h"\nstatic const struct{int(*send)')
s=s.replace('return dst==DATE99_DEST?date99_accept(dst,p):cp_reset_send_backup99(dst,p);','return dst==DATE99_DEST?date99_accept(dst,p):sync100_route(dst,p);')
# Prototype before wrapper; implementation can refer to previous reset and CP99.
s=s.replace('static int cp_reset_send99(', 'static int sync100_route(W,void*);\nstatic int cp_reset_send99(')
s=s.replace('int init_module(void){int rc=date99_start();','int init_module(void){int rc=sync100_start();if(rc)return rc;rc=date99_start();')
s=s.replace('if(rc)return rc;rc=osal_reg_public(&owner);','if(rc){sync100_stop();return rc;}rc=osal_reg_public(&owner);')
s=s.replace('else date99_stop();printk(', 'else {date99_stop();sync100_stop();}printk(')
s=s.replace('date99_stop();if(work)', 'date99_stop();sync100_stop();if(work)')
put('fx3-cp-backup-v4-sync100.c',s)
s=(H/'fx3-cp-backup-reset-v3-date99-module-unit.c').read_text().replace('fx3-cp-backup-reset-v3-date99.c','fx3-cp-backup-v4-sync100.c').replace('fx3_cp_backup_date99_v3','fx3_cp_backup_sync100_v4')
put('fx3-cp-backup-v4-sync100-module-unit.c',s)
print('new version sources created; not yet frozen')
