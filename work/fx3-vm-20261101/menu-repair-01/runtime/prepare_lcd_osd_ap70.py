from pathlib import Path
import json, subprocess, os, hashlib, plistlib
R=Path(__file__).resolve().parent;H=R/'helpers'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
s=(H/'fx3-capid-v24.c').read_text()
code=r'''
/* Bounded software acceptance from vdf011a-0159-proof.json; no hardware completion. */
static struct lcd_shadow {unsigned char payload[6],selector,brightness;unsigned int pending_hardware,updates;} lcd;
static struct osd_shadow {unsigned char legacy[4];unsigned int pending_f030,updates;} osd;
static const unsigned char lcd_packet[14]={0x0d,0x20,0x1a,1,14,0,1,0x80,1,14,0,14,6,0};
static int lcd_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;
 if(msg_size(request)!=14||memcmp(request,lcd_packet,14))return -1024;
 unsigned int from=source(request);if(!local(from))return -1024;
 int slot=-1;for(int i=0;i<8;i++)if(!live[i].p){slot=i;break;}if(slot<0)return -1021;
 void *reply=0;int rc=allocate(from,&reply,12,1);
 if(reply&&reply==request){fault=1;return -1021;}for(int i=0;i<8;i++)if(reply&&reply==live[i].p){fault=1;return -1021;}
 if(rc||!reply){if(reply&&release(from,reply))fault=1;return rc?rc:-1021;}
 struct lcd_shadow before=lcd;
 memcpy(lcd.payload,(unsigned char *)request+8,6);lcd.selector=1;lcd.brightness=6;lcd.pending_hardware=1;lcd.updates++;
 const unsigned char completion[12]={0x0d,0x20,0x1a,0x11,12,0,1,0x80,0,0,0,0};memcpy(reply,completion,12);
 set_source(reply,0x92840747);live[slot].p=reply;live[slot].dst=from;live[slot].command=0x11a;live[slot].serial=++serial;rc=send_msg(from,reply);
 if(rc){lcd=before;memset(&live[slot],0,sizeof live[slot]);if(release(from,reply))fault=1;return rc;}
 int freed=release(0x92840747,request);if(freed)fault=1;
 dprintf(2,"FX3_LCD_BRIGHTNESS_COMMIT command=0x11a completion=0x111a source=%#x selector=1 brightness=6 pending_hardware=1 updates=%u lease=%lu request_free=%d software_backend=1 physical_complete=0\n",from,lcd.updates,live[slot].serial,freed);return 0;
}
static int osd_dispatch(void *request){
 if(fault||!model.initialized||process_owner!=syscall(172)||!request)return -1021;
 const unsigned char header[8]={0x0d,0x20,0x59,1,10,0,1,0x80};
 if(msg_size(request)!=10||memcmp(request,header,8))return -1024;
 const unsigned char *p=request;if(p[9]||(p[8]!=3&&p[8]!=7)||!local(source(request)))return -1024;
 struct osd_shadow before=osd;memset(osd.legacy,0,4);osd.legacy[0]=p[8];osd.pending_f030=1;osd.updates++;
 unsigned int from=source(request);int rc=release(0x92840747,request);
 if(rc){osd=before;fault=1;return rc;}
 dprintf(2,"FX3_OSD_ONOFF_ACCEPT command=0x159 source=%#x mask=%u pending_f030=1 updates=%u reply_added=0 request_free=0 software_backend=1 physical_complete=0\n",from,osd.legacy[0],osd.updates);return 0;
}
'''
pos=s.index('extern long pread(');s=s[:pos]+code+s[pos:]
pos=s.index(' const char *audio_profile=');s=s[:pos]+''' const char *lcd_profile=getenv("FX3_LCD_OSD");
 if(enabled&&dst==0x92840747&&request&&lcd_profile&&!strcmp(lcd_profile,"captured-v1")&&msg_size(request)>=4){unsigned int h;memcpy(&h,request,4);if(h==0x011a200d||h==0x0159200d){int rc=h==0x011a200d?lcd_dispatch(request):osd_dispatch(request);leave();*__errno_location()=saved;return rc;}}
'''+s[pos:]
s=s.replace('if(!(dst==0x92840747&&(h==0x0118200d||h==0x032e200d||h==0x033d200d))||count++>=6)return;', 'if(dst!=0x92840747||count++>=64)return;')
s=s.replace('count++<64&&n<=1024','count++<256&&n<=1024')
assert not (H/'fx3-capid-v25.c').exists();(H/'fx3-capid-v25.c').write_text(s)
s=(H/'check-release-inhibit-transport.c').read_text().replace('fx3-capid-v23.c','fx3-capid-v25.c')
pos=s.index(' pthread_t threads[8]');test=r'''
 reset();model.initialized=1;in_size=14;lcd=(struct lcd_shadow){0};memcpy(request,lcd_packet,14);
 assert(!lcd_dispatch(request)&&lcd.pending_hardware&&lcd.selector==1&&lcd.brightness==6&&lcd.updates==1&&last_free==request&&!memcmp(reply,"\x0d\x20\x1a\x11\x0c\x00\x01\x80\x00\x00\x00\x00",12));assert(!osal_free_msg(src,reply)&&!live[0].p);
 struct lcd_shadow prevlcd=lcd;send_rc=-1020;unsigned int before=free_count;assert(lcd_dispatch(request)==-1020&&!memcmp(&lcd,&prevlcd,sizeof lcd)&&free_count==before+1&&last_free==reply&&!live[0].p);send_rc=0;
 alloc_rc=-1022;before=free_count;assert(lcd_dispatch(request)==-1022&&!memcmp(&lcd,&prevlcd,sizeof lcd)&&free_count==before);alloc_rc=0;
 for(int i=0;i<14;i++){request[i]^=1;unsigned int sends=send_count;before=free_count;assert(lcd_dispatch(request)==-1024&&sends==send_count&&before==free_count&&!memcmp(&lcd,&prevlcd,sizeof lcd));request[i]^=1;}
 in_size=13;assert(lcd_dispatch(request)==-1024);in_size=15;assert(lcd_dispatch(request)==-1024);
 reset();model.initialized=1;in_size=10;osd=(struct osd_shadow){0};const unsigned char osdp[10]={0x0d,0x20,0x59,1,10,0,1,0x80,7,0};memcpy(request,osdp,10);
 assert(!osd_dispatch(request)&&osd.legacy[0]==7&&!osd.legacy[1]&&!osd.legacy[2]&&!osd.legacy[3]&&osd.pending_f030&&!send_count&&free_count==1&&last_free==request);
 request[8]=3;assert(!osd_dispatch(request)&&osd.legacy[0]==3&&osd.updates==2&&!send_count&&free_count==2);struct osd_shadow prevosd=osd;
 for(int i=0;i<256;i++){if(i==3||i==7)continue;request[8]=i;before=free_count;assert(osd_dispatch(request)==-1024&&before==free_count&&!send_count&&!memcmp(&osd,&prevosd,sizeof osd));}
 memcpy(request,osdp,10);for(int i=0;i<10;i++){request[i]^=0x80;assert(osd_dispatch(request)==-1024&&!memcmp(&osd,&prevosd,sizeof osd));request[i]^=0x80;}in_size=9;assert(osd_dispatch(request)==-1024);in_size=11;assert(osd_dispatch(request)==-1024);
 puts("LCD_OSD_PASS exact14B/native111a/leasefree/pendinghardware, sendrollback/allocfailure/allbyte_reject, OSD3and7/legacy4B/pendingf030/NO_REPLY/allmask_reject");
'''
s=s[:pos]+test+s[pos:];(H/'check-lcd-osd-transport.c').write_text(s)
args=['clang','-O1','-g','-fsanitize=address,undefined','-fno-sanitize-recover=all','-pthread',str(H/'check-lcd-osd-transport.c'),str(H/'capid-service.c'),str(H/'fx3-sa-address-core.c'),'-o',str(H/'check-lcd-osd-transport')]
v=subprocess.run(args,capture_output=True,text=True);assert not v.returncode,v.stderr
t=subprocess.run([args[-1]],capture_output=True,text=True,timeout=30);(H/'lcd-osd-transport-host-check.json').write_text(json.dumps(dict(args=args,compile_stderr=v.stderr,exit=t.returncode,stdout=t.stdout,stderr=t.stderr),indent=2)+'\n');assert not t.returncode,t.stderr;print(t.stdout)
x=json.loads((H/'fx3-capid-v24-build.json').read_text());args=[a.replace('fx3-capid-v24','fx3-capid-v25') for a in x['args']];env=os.environ.copy();env.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));v=subprocess.run(args,capture_output=True,text=True,env=env);assert not v.returncode,v.stderr
x.update(args=args,source_sha256=hashlib.sha256((H/'fx3-capid-v25.c').read_bytes()).hexdigest(),output_sha256=hashlib.sha256((H/'fx3-capid-v25.so').read_bytes()).hexdigest(),change='CapturedLCD011a softwareacceptance/pendinghardware/111a; OSD0159 masks3or7 silentacceptance/pendingf030; bounded passive64 VDFstacks,256 requests');(H/'fx3-capid-v25-build.json').write_text(json.dumps(x,indent=2)+'\n')
s=(R/'build_audio_query_candidate69.py').read_text().replace('ap69-audio-query-observe','ap70-lcd-osd').replace('candidate69.json','candidate70.json').replace('fx3-capid-v24.so','fx3-capid-v25.so').replace("base=R/'ap68-release-inhibit/candidate68.json'","base=R/'ap69-audio-query-observe/candidate69.json'")
s=s.replace('init=data.decode();data=init.encode()','init=data.decode().replace("FX3_CAPID_STORAGE=reserved-v1 ","FX3_CAPID_STORAGE=reserved-v1 FX3_LCD_OSD=captured-v1 ");data=init.encode()')
s=s.replace("'FX3_RELEASE_INHIBIT_COMMIT']","'FX3_RELEASE_INHIBIT_COMMIT','FX3_LCD_BRIGHTNESS_COMMIT','FX3_OSD_ONOFF_ACCEPT']")
s=s.replace('Explicit inactiveMonitorLUT','ExplicitLCDselector1brightness6/pendinghardware/111a softwareacceptance; OSDmask3or7/pendingf030/no_reply. Explicit inactiveMonitorLUT')
s=s.replace('Aggregatev17 passiveboundedprofile/VDFstack; existingv12GPEuniformmodel retained','v25 LCD011a/OSD0159 auditedboundedsoftwareacceptance; passiveVDFstacks64/request256; existingv12GPE retained')
(R/'build_lcd_osd_candidate70.py').write_text(s)
