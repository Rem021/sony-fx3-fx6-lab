from pathlib import Path
import json,hashlib,subprocess,os
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-capid-v38.c').read_text();s=s.replace('static void fr_capture_local(const unsigned char p[40]){unsigned op=', 'static void fr_capture_local(const unsigned char p[40]){unsigned op=');s=s.replace('!(op==0x8020||op==0x8021||op==0x802a)','!(op==0x8020||op==0x8021||op==0x8024||op==0x802a)')
a='static int pin_duplicate_free(unsigned dst,void *p){if(!p)return 0;';b='static int pin_duplicate_free(unsigned dst,void *p){if(!p)return 0;if(msg_size(p)!=56){pin_forget_retired(p);return 0;}'
assert a in s;s=s.replace(a,b)
a='static int panel_duplicate_free(unsigned dst,void *p){for(int i=0;';b='static int panel_duplicate_free(unsigned dst,void *p){if(p&&msg_size(p)!=12){for(int i=0;i<32;i++)if(panel_retired[i].pointer==p)memset(panel_retired+i,0,sizeof panel_retired[i]);return 0;}for(int i=0;';assert a in s;s=s.replace(a,b)
a='unsigned char captured[40];int capture=0;const char *fp=getenv("FX3_ADF_FILE");if(p&&fp&&!strcmp(fp,"muted-user-v1")&&msg_size(p)==40){memcpy(captured,p,40);capture=1;}'
b='unsigned char captured[40]={0};int capture=0;unsigned captured_size=0;const char *fp=getenv("FX3_ADF_FILE");if(p&&fp&&!strcmp(fp,"muted-user-v1")){unsigned n=msg_size(p);if(n==24||n==40){memcpy(captured,p,n);unsigned op=ff_get(captured,2);if(op>=0x8020&&op<=0x802a&&ff_get(captured+8,2)==(n-24)/16){capture=1;captured_size=n;}}}'
assert a in s;s=s.replace(a,b)
a='ff_capture_local(captured);fr_capture_local(captured);';b='ff_capture_local(captured);fr_capture_local(captured);if(ff_get(captured+16,4)>=0x1d9&&ff_get(captured+16,4)<=0x1dc||fr_local_index(ff_get(captured+12,4))>=0){dprintf(2,"FX3_FACE_LOCAL_NATIVE_REPLY op=%#x bytes=%u original_free=0 raw=",ff_get(captured,2),captured_size);for(unsigned j=0;j<captured_size;j++)dprintf(2,"%02x",captured[j]);dprintf(2,"\\n");}'
assert a in s;s=s.replace(a,b)
(H/'fx3-capid-v39.c').write_text(s)
a=[x.replace('fx3-capid-v38','fx3-capid-v39') for x in json.loads((H/'fx3-capid-v38-build.json').read_text())['args']];e=os.environ.copy();e.update(ZIG_GLOBAL_CACHE_DIR=str(R/'toolchains/zig-cache'),ZIG_LOCAL_CACHE_DIR=str(R/'toolchains/zig-local-cache'));p=subprocess.run(a,env=e,capture_output=True,text=True);assert not p.returncode,p.stderr;(H/'fx3-capid-v39-build.json').write_text(json.dumps({'args':a,'exit':0,'source_sha256':hashlib.sha256((H/'fx3-capid-v39.c').read_bytes()).hexdigest(),'output_sha256':hashlib.sha256((H/'fx3-capid-v39.so').read_bytes()).hexdigest()},indent=2)+'\n');print('v39 native24B/8024 capture built')
