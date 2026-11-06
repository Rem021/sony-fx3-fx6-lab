from pathlib import Path
import subprocess,json
R=Path(__file__).resolve().parent;H=R/'helpers';s=r'''
#include <assert.h>
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
#include "fx3-cp-backup-observe-v1.c"
static unsigned size=4096,regcalls,unregs;static int regresult;static const void *received;
int printk(const char *f,...){(void)f;return 0;}int osal_reg_public(const void *p){regcalls++;received=p;return regresult;}int osal_unreg_public(void){unregs++;return 0;}W osal_msg_size(const void *p){assert(p);return size;}W osal_get_msg_src(const void *p){assert(p);return 0x2a610900;}
int main(void){assert(!init_module()&&registered&&regcalls==1&&received==&owner&&owner.send==capture_send&&!owner.sync);unsigned char input[40]={0x33,0,0,0,0,0,0,0,0x11,8,0x3e,0x90,0,9,0x61,0x2a,1,0,0,0,1,0,0,0,2,0,0,0,0,0,0,0,2,0,0,0,1,0,0,0},copy[40];memcpy(copy,input,40);assert(!owner.send(0x903e0811,input)&&captures==1&&!memcmp(copy,input,40));size=40;assert(!owner.send(0x903e0811,input)&&captures==2);size=39;assert(!owner.send(0x903e0811,input)&&captures==2);assert(!owner.send(0x90030001,input)&&captures==2&&!memcmp(copy,input,40));cleanup_module();assert(unregs==1&&!registered);regresult=-1018;assert(init_module()==-1018&&!registered);cleanup_module();assert(unregs==1);puts("CAPTURE88_PASS original_public_tableABI/no_reply_no_free/body_unchanged/page4096_orlogical40/short_guard/uniqueowner_failure_preserves_existing");}
''';p=H/'check-capture88.c';p.write_text(s);a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all',str(p),'-o',str(p.with_suffix(''))];q=subprocess.run(a,text=True,capture_output=True);assert not q.returncode,q.stderr;q=subprocess.run([str(p.with_suffix(''))],text=True,capture_output=True);(H/'capture88-host-check.json').write_text(json.dumps({'args':a,'exit':q.returncode,'stdout':q.stdout,'stderr':q.stderr},indent=2)+'\n');assert not q.returncode,q.stderr;print(q.stdout)
