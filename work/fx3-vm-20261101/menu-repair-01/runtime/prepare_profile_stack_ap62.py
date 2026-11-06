from pathlib import Path
import json,os,hashlib,subprocess
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-capid-v16.c').read_text();pos=s.index('int osal_snd_msg(')
code='''extern long pread(int,void *,size_t,long);
static void profile_stack(unsigned int dst,void *request,void *frame){
 static unsigned int count;unsigned int h=0;if(request&&msg_size(request)>=4)memcpy(&h,request,4);
 if(!(dst==0x909c015b||(dst==0x92840747&&h==0x0118200d))||count++>=6)return;
 int fd=open("/proc/self/mem",0);if(fd<0)return;unsigned long start=(unsigned long)frame,fp=start;
 dprintf(2,"FX3_PROFILE_STACK_BEGIN destination=%#x header=%#x tid=%ld frame=%p\\n",dst,h,syscall(178),frame);
 for(unsigned int i=0;i<12;i++){unsigned long row[2];if(fp<start||fp-start>0x20000||(fp&15)||pread(fd,row,16,fp)!=16)break;
 struct cap_dl_info info={0};dladdr((void *)row[1],&info);dprintf(2,"FX3_PROFILE_FRAME depth=%u fp=%#lx lr=%#lx module=%s relative=%#lx\\n",i,fp,row[1],info.file?info.file:"?",info.base?row[1]-(unsigned long)info.base:0);
 if(row[0]<=fp)break;fp=row[0];}close(fd);dprintf(2,"FX3_PROFILE_STACK_END destination=%#x\\n",dst);
}
''';s=s[:pos]+code+s[pos:];s=s.replace('int saved=*__errno_location(),rc;enter();initialize();leave();','int saved=*__errno_location(),rc;enter();initialize();leave();\n profile_stack(dst,request,__builtin_frame_address(0));',1);(H/'fx3-capid-v17.c').write_text(s)
x=json.loads((H/'fx3-capid-v16-build.json').read_text());args=[a.replace('fx3-capid-v16','fx3-capid-v17') for a in x['args']];env=os.environ.copy();env.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));v=subprocess.run(args,capture_output=True,text=True,env=env);assert not v.returncode,v.stderr;x.update(args=args,source_sha256=hashlib.sha256(s.encode()).hexdigest(),output_sha256=hashlib.sha256((H/'fx3-capid-v17.so').read_bytes()).hexdigest(),change='Bounded6 read-only framechain snapshots for909c015b and VDF0118; all providers/nativeownership unchanged');(H/'fx3-capid-v17-build.json').write_text(json.dumps(x,indent=2)+'\n')
s=(R/'build_next_wait_candidate61.py').read_text().replace('ap61-next-wait','ap62-profile-stack').replace('candidate61.json','candidate62.json').replace('fx3-capid-v16.so','fx3-capid-v17.so');s=s.replace("base=R/'ap55-futex-lock/candidate55.json'","base=R/'ap61-next-wait/candidate61.json'");s=s.replace("'Aggregatev13 FX3 24x32B planevalidation/doublebuffer cache, pendingf024, displaydomain590000/nativeleases/rollback'","'Aggregatev17 passiveboundedprofile/VDFstack; existingv12GPEuniformmodel retained'");(R/'build_profile_stack_candidate62.py').write_text(s)
