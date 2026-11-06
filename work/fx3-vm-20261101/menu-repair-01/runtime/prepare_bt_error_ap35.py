from pathlib import Path
import json,hashlib,os,subprocess
R=Path(__file__).resolve().parent;s=(R/'helpers/fx3-gpe-observe-v5.c').read_text();s+='''
void bt_error_place(void *,unsigned short,unsigned int) __asm__("_ZN8BTUtils_6BTBlog10errorPlaceEtj");
void bt_error_place(void *self,unsigned short group,unsigned int line){
 int before=*__errno_location();struct app_dl_info info={0};void *caller=__builtin_return_address(0);dladdr(caller,&info);
 dprintf(2,"FX3_BT_ERROR self=%p group=%u line=%u caller=%s+%#lx original_delegated=1\\n",self,group,line,info.file?info.file:"?",info.base?(U)caller-(U)info.base:0);
 void (*fn)(void *,unsigned short,unsigned int)=dlsym((void *)-1,"_ZN8BTUtils_6BTBlog10errorPlaceEtj");if(!fn||fn==bt_error_place)_exit(126);
 *__errno_location()=before;fn(self,group,line);
}
''';(R/'helpers/fx3-gpe-observe-v7.c').write_text(s)
v=json.loads((R/'helpers/fx3-gpe-observe-v5-build.json').read_text());args=[a.replace('fx3-gpe-observe-v5.c','fx3-gpe-observe-v7.c').replace('fx3-gpe-observe-v5.so','fx3-gpe-observe-v7.so') for a in v['args']];env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(R/'toolchains/zig-cache');env['ZIG_LOCAL_CACHE_DIR']=str(R/'toolchains/zig-local-cache');p=subprocess.run(args,env=env,capture_output=True,text=True);assert p.returncode==0,p.stderr;(R/'helpers/fx3-gpe-observe-v7-build.json').write_text(json.dumps({'args':args,'exit':p.returncode,'stderr':p.stderr,'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'scope':'passive original Bluetooth errorPlace caller/line observation; no unavailable policy'},indent=2)+'\n')
s=(R/'prepare_bt_ap34.py').read_text().replace('ap34-bluetooth-unavailable','ap35-bt-error').replace('candidate34.json','candidate35.json').replace('fx3-gpe-observe-v6.so','fx3-gpe-observe-v7.so').replace('FX3_HDMI_REGISTRATION=software-v1 FX3_BLUETOOTH_POLICY=unavailable-v1 ','FX3_HDMI_REGISTRATION=software-v1 ')
s=s.replace("['FX3_PLATFORM_UNAVAILABLE']","['FX3_BT_ERROR']").replace('Explicit BLE lifecycle unavailable profile after AP33 native NULLlogger fault. Native IM dlopen failure and app failure handling retained, no success injected.','Passive BLE error observation, original calls delegated; no loader rejection.')
(R/'prepare_bt_ap35.py').write_text(s)
