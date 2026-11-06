from pathlib import Path
import json,hashlib,os,subprocess
R=Path(__file__).resolve().parent;s=(R/'helpers/fx3-gpe-observe-v5.c').read_text();s=s.replace('extern int strcmp(const char *,const char *);','extern int strcmp(const char *,const char *);\nextern char *getenv(const char *);')
a='void *dlopen(const char *name,int flags) {';z='''void *dlopen(const char *name,int flags) {
 /* Explicit no-Bluetooth platform capability. Native IM sees its own dlopen
  * failure path; do not create a successful Bluetooth owner or patch error logging. */
 const char *policy=getenv("FX3_BLUETOOTH_POLICY");
 if(policy&&!strcmp(policy,"unavailable-v1")&&name&&
    (!strcmp(name,"libInfraBluetoothLowEnergy.so")||!strcmp(name,"/usr/lib/libInfraBluetoothLowEnergy.so"))){
  dprintf(2,"FX3_PLATFORM_UNAVAILABLE library=%s reason=no_bluetooth_platform profile=unavailable-v1 native_im_failure_path=1\\n",name);
  *__errno_location()=19;return 0;
 }
''';assert a in s;s=s.replace(a,z);(R/'helpers/fx3-gpe-observe-v6.c').write_text(s)
v=json.loads((R/'helpers/fx3-gpe-observe-v5-build.json').read_text());args=[a.replace('fx3-gpe-observe-v5.c','fx3-gpe-observe-v6.c').replace('fx3-gpe-observe-v5.so','fx3-gpe-observe-v6.so') for a in v['args']];env=os.environ.copy();env['ZIG_GLOBAL_CACHE_DIR']=str(R/'toolchains/zig-cache');env['ZIG_LOCAL_CACHE_DIR']=str(R/'toolchains/zig-local-cache');p=subprocess.run(args,env=env,capture_output=True,text=True);assert p.returncode==0,p.stderr;(R/'helpers/fx3-gpe-observe-v6-build.json').write_text(json.dumps({'args':args,'exit':p.returncode,'stderr':p.stderr,'source_sha256':hashlib.sha256(s.encode()).hexdigest(),'scope':'AP33 null logger after original BLE wait on uninitialized sem; explicit unavailable-v1 platform capability returns NULL on named lifecycle dlopen, native IM failure path preserved; no success/ACK'},indent=2)+'\n')
# Derive an immutable new candidate, preserving original assets and registration service.
s=(R/'prepare_hdmi_ap33.py').read_text().replace("ap33-hdmi-registration'","ap34-bluetooth-unavailable'").replace("ap32-app-wait/candidate32.json","ap33-hdmi-registration/candidate33.json").replace('candidate33.json','candidate34.json')
# restore base path after blanket output rename
s=s.replace('ap33-hdmi-registration/candidate34.json','ap33-hdmi-registration/candidate33.json')
a="init=init.replace(a,'FX3_HDMI_REGISTRATION=software-v1 '+a+'/simulation/fx3-hdmi-registration-v1.so:');data=init.encode()"
z="init=init.replace('FX3_HDMI_REGISTRATION=software-v1 ','FX3_HDMI_REGISTRATION=software-v1 FX3_BLUETOOTH_POLICY=unavailable-v1 ').replace('fx3-gpe-observe-v5.so','fx3-gpe-observe-v6.so');data=init.encode()";assert a in s;s=s.replace(a,z)
s=s.replace("helper=R/'helpers/fx3-hdmi-registration-v1.so';entries.append(['simulation/fx3-hdmi-registration-v1.so'","helper=R/'helpers/fx3-gpe-observe-v6.so';entries.append(['simulation/fx3-gpe-observe-v6.so'")
s=s.replace("v['required_markers']+=['FX3_HDMI_REG_COMMIT','FX3_HDMI_REG_NATIVE_FREE']","v['required_markers']+=['FX3_PLATFORM_UNAVAILABLE'];v['scope']+=' Explicit BLE lifecycle unavailable profile after AP33 native NULLlogger fault. Native IM dlopen failure and app failure handling retained, no success injected.'")
s=s.replace("'add one explicitly-enabled software HDMI registration helper'","'add GPE/app observer v6 with explicit Bluetooth unavailable policy'")
(R/'prepare_bt_ap34.py').write_text(s);print('compiled v6 and prepared AP34 builder')
