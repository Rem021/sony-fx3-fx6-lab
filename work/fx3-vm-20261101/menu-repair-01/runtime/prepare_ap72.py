from pathlib import Path
import json,subprocess,os
R=Path(__file__).resolve().parent;H=R/'helpers'
s=(H/'fx3-capid-v25.c').read_text()
code=r'''
static void *muted_memory;
static unsigned int muted_volume_updates,muted_address_queries;
static int muted_bind(void){
 if(muted_memory)return 0;
 int fd=open("/tmp/fx3-adf-muted.claim",0x200c1,0600);if(fd<0)return -1021;
 dprintf(fd,"pid=%ld physical=41da00000 bytes=10000 muted=1 original_sound=0\n",process_owner);close(fd);
 char cmd[4096]={0};fd=open("/proc/cmdline",0);long n=fd<0?-1:read(fd,cmd,sizeof cmd-1);if(fd>=0)close(fd);
 if(n<=0||!strstr(cmd,"memrsv=0x00010000@0x41da00000:uc")){fault=1;return -1021;}
 fd=open("/dev/mem",2);void *p=fd<0?(void *)-1:mmap(0,0x10000,3,1,fd,0x41da00000UL);if(fd>=0)close(fd);
 if(p==(void *)-1){fault=1;return -1021;}memset(p,0,0x10000);muted_memory=p;
 dprintf(2,"FX3_ADF_MUTED_BIND physical=0x41da00000 bytes=65536 muted=1 original_sound=0 playback_supported=0\n");return 0;
}
static int muted_dispatch(void *request,unsigned int command){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;
 const unsigned char volume[10]={0x0d,0x20,0x2e,3,10,0,1,0x80,8,0},query[8]={0x0d,0x20,0x3d,3,8,0,1,0x80};
 unsigned int size=command==0x32e?10:8,out_size=command==0x32e?12:24;
 if((command!=0x32e&&command!=0x33d)||msg_size(request)!=size||memcmp(request,command==0x32e?volume:query,size))return -1024;
 unsigned int from=source(request);if(!local(from))return -1024;
 if(command==0x33d){int rc=muted_bind();if(rc)return rc;}
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,out_size,1);
 if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 unsigned char *p=reply;memset(p,0,out_size);p[0]=0x0d;p[1]=0x20;p[2]=command&255;p[3]=0x13;p[4]=out_size;p[6]=1;p[7]=0x80;
 if(command==0x33d){unsigned long long physical=0x41da00000ULL;memcpy(p+16,&physical,8);}
 set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=command;live[slot].serial=++serial;rc=send_msg(from,reply);
 if(rc){memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 if(command==0x32e)muted_volume_updates++;else muted_address_queries++;
 int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_ADF_MUTED_COMMIT command=%#x source=%#x status=0 bytes=%u physical=%#llx wire_volume=8 internal_volume=7 muted=1 original_sound=0 request_free=%d lease=%lu\n",command,from,out_size,command==0x33d?0x41da00000ULL:0ULL,freed,live[slot].serial);return 0;
}
'''
s=s.replace('extern long pread(',code+'\nextern long pread(')
pos=s.index(' const char *audio_profile=')
s=s[:pos]+''' const char *muted_profile=getenv("FX3_ADF_MUTED");
 if(enabled&&dst==0x92840747&&request&&muted_profile&&!strcmp(muted_profile,"silent-storage-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x032e200d||h==0x033d200d){int rc=muted_dispatch(request,h>>16);leave();*__errno_location()=saved;return rc;}}
'''+s[pos:]
(H/'fx3-capid-v26.c').write_text(s)
t=(H/'check-lcd-osd-transport.c').read_text().replace('fx3-capid-v25.c','fx3-capid-v26.c');pos=t.index(' pthread_t threads[8]');t=t[:pos]+r'''
 reset();model.initialized=1;in_size=10;const unsigned char vol[10]={13,32,46,3,10,0,1,128,8,0};memcpy(request,vol,10);assert(!muted_dispatch(request,0x32e)&&reply[2]==0x2e&&reply[3]==0x13&&reply[4]==12&&last_free==request);assert(!osal_free_msg(src,reply));
 for(int i=0;i<10;i++){request[i]^=1;assert(muted_dispatch(request,0x32e)==-1024);request[i]^=1;}
 send_rc=-1020;assert(muted_dispatch(request,0x32e)==-1020&&!live[0].p&&last_free==reply);send_rc=0;alloc_rc=-1022;assert(muted_dispatch(request,0x32e)==-1022&&!live[0].p);alloc_rc=0;
 in_size=8;const unsigned char qry[8]={13,32,61,3,8,0,1,128};memcpy(request,qry,8);unsigned char backing[65536]={0};muted_memory=backing;assert(!muted_dispatch(request,0x33d)&&reply[4]==24&&!reply[8]&&!reply[12]);unsigned long long phys=0;memcpy(&phys,reply+16,8);assert(phys==0x41da00000ULL);assert(!osal_free_msg(src,reply));
 for(int i=0;i<8;i++){request[i]^=1;assert(muted_dispatch(request,0x33d)==-1024);request[i]^=1;}in_size=9;assert(muted_dispatch(request,0x33d)==-1024);in_size=8;assert(muted_dispatch(request,0x33e)==-1024);puts("ADF_MUTED_PASS strict_packets/native_completion/address64/ownership/rollback/invalid_bytes");
'''+t[pos:];(H/'check-adf-muted-transport.c').write_text(t)
a=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread',str(H/'check-adf-muted-transport.c'),str(H/'capid-service.c'),str(H/'fx3-sa-address-core.c'),'-o',str(H/'check-adf-muted-transport')];subprocess.run(a,check=True);v=subprocess.run([a[-1]],capture_output=True,text=True);(H/'adf-muted-host-check.json').write_text(json.dumps(dict(args=a,exit=v.returncode,stdout=v.stdout,stderr=v.stderr),indent=2));assert not v.returncode,v.stderr
x=json.loads((H/'fx3-capid-v25-build.json').read_text());a=[i.replace('fx3-capid-v25','fx3-capid-v26') for i in x['args']];e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));subprocess.run(a,env=e,check=True);(H/'fx3-capid-v26-build.json').write_text(json.dumps(dict(args=a,exit=0),indent=2))
s=(R/'build_lcd_osd_candidate70.py').read_text().replace("D=R/'ap70-lcd-osd'","D=R/'ap72-adf-muted'").replace("base=R/'ap69-audio-query-observe/candidate69.json'","base=R/'ap71-icrypt-load-r2/candidate71.json'").replace("(D/'candidate70.json')","(D/'candidate72.json')").replace('fx3-capid-v25.so','fx3-capid-v26.so')
s=s.replace('init=data.decode().replace("FX3_CAPID_STORAGE=reserved-v1 ","FX3_CAPID_STORAGE=reserved-v1 FX3_LCD_OSD=captured-v1 ")','init=data.decode().replace("FX3_CAPID_STORAGE=reserved-v1 ","FX3_CAPID_STORAGE=reserved-v1 FX3_ADF_MUTED=silent-storage-v1 ")')
f=(R/'prepare_remote_dmm_ap49_r2.py').read_text();a=f.index('# Reserve a private gap');b=f.index("dtb=D/'guest.dtb'",a);reserve=f[a:b].replace('0x41d900000','0x41da00000').replace('0x100000','0x10000').replace('0x00100000','0x00010000').replace('remoteDMM','mutedADF')
s=s.replace("dtb=D/'guest.dtb'",reserve+"dtb=D/'guest.dtb'");s=s.replace("(D/'candidate72.json').write_text", "v['required_markers']+=['FX3_ADF_MUTED_BIND','FX3_ADF_MUTED_COMMIT'];v['scope']+=' MutedADF independent64KiB 41da00000; original_sound=0 playback=unsupported.';(D/'candidate72.json').write_text");(R/'build_adf_candidate72.py').write_text(s);subprocess.run(['python3',str(R/'build_adf_candidate72.py')],check=True)
