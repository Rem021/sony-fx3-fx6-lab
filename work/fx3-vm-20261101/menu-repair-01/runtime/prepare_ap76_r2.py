from pathlib import Path
import json,os,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-capid-v28.c').read_text();s=s.replace('if(dst==0x02820746){int rc=ff_icdt(request);leave();*__errno_location()=saved;return rc;}','/* The audited ICDT entry is osal_snd_sync_msg, not asynchronous send. */')
s+=r'''
int osal_snd_sync_msg(unsigned int dst,void *request){
 int saved=*__errno_location();enter();initialize();leave();const char *profile=getenv("FX3_ADF_FILE");
 if(enabled&&dst==0x02820746&&profile&&!strcmp(profile,"muted-user-v1")){
  profile_stack(dst,request,__builtin_frame_address(0));unsigned int n=request?msg_size(request):0;
  if(request&&n==48){const unsigned char *p=request;char raw[97];const char *hex="0123456789abcdef";for(unsigned int i=0;i<48;i++){raw[2*i]=hex[p[i]>>4];raw[2*i+1]=hex[p[i]&15];}raw[96]=0;dprintf(2,"FX3_ICDT_SYNC_CAPTURE tid=%ld destination=%#x bytes=48 raw=%s kernel_sync_delegated=0\n",syscall(178),dst,raw);}
  enter();int rc=ff_icdt(request);leave();*__errno_location()=saved;return rc;
 }
 int (*fn)(unsigned int,void *)=dlsym((void *)-1,"osal_snd_sync_msg");if(!fn)_exit(126);*__errno_location()=saved;return fn(dst,request);
}
''';(H/'fx3-capid-v29.c').write_text(s)
t=(H/'check-adf-file-transport.c').read_text().replace('fx3-capid-v28.c','fx3-capid-v29.c');t=t.replace('send_rc=-1020;assert(ff_icdt(request)', 'setenv("FX3_ADF_FILE","muted-user-v1",1);send_rc=-1020;assert(osal_snd_sync_msg(0x02820746,request)').replace('assert(!ff_icdt(request)', 'assert(!osal_snd_sync_msg(0x02820746,request)').replace('assert(ff_icdt(request)', 'assert(osal_snd_sync_msg(0x02820746,request)');(H/'check-adf-file-sync-transport.c').write_text(t)
a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread',str(H/'check-adf-file-sync-transport.c'),str(H/'capid-service.c'),str(H/'fx3-sa-address-core.c'),'-o',str(H/'check-adf-file-sync-transport')];v=subprocess.run(a,capture_output=True,text=True);assert not v.returncode,v.stderr;x=subprocess.run([a[-1]],capture_output=True,text=True,timeout=40);(H/'adf-file-sync-host-check.json').write_text(json.dumps(dict(args=a,exit=x.returncode,stdout=x.stdout,stderr=x.stderr),indent=2));assert not x.returncode,x.stderr
x=json.loads((H/'fx3-capid-v28-build.json').read_text());a=[i.replace('fx3-capid-v28','fx3-capid-v29') for i in x['args']];e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));v=subprocess.run(a,env=e,capture_output=True,text=True);assert not v.returncode,v.stderr;(H/'fx3-capid-v29-build.json').write_text(json.dumps(dict(args=a,exit=0,source_sha256=hashlib.sha256((H/'fx3-capid-v29.c').read_bytes()).hexdigest(),output_sha256=hashlib.sha256((H/'fx3-capid-v29.so').read_bytes()).hexdigest()),indent=2))
s=(R/'build_file_candidate76.py').read_text().replace("D=R/'ap76-adf-file-icdt'","D=R/'ap76-adf-file-icdt-r2'").replace('fx3-capid-v28.so','fx3-capid-v29.so').replace("(D/'candidate76.json').write_text", "v['required_markers']+=['FX3_ICDT_SYNC_CAPTURE'];(D/'candidate76.json').write_text");(R/'build_file_candidate76_r2.py').write_text(s);subprocess.run(['python3',str(R/'build_file_candidate76_r2.py')],check=True)
