from pathlib import Path
import json,subprocess,hashlib
R=Path(__file__).resolve().parent;H=R/'helpers';s=(H/'fx3-capid-v44.c').read_text();a=s.index('static void reserve_table(void)');s=s[:a]+'#include "fx3-synth-key-script-v1.inc"\n'+s[a:];s=s.replace('int saved=*__errno_location(),rc;enter();initialize();leave();','int saved=*__errno_location(),rc;enter();initialize();leave();sk_start_once();sk_observe_internal(dst,request);',1);(H/'fx3-capid-v45-keys.c').write_text(s)
s=(H/'fx3-preset-context-v2-screen.c').read_text();a=s.index('static int peek(');s=s[:a]+'''static U native_dialog_open_ns;static unsigned native_screen_target;
U fx3_native_screen_open_snapshot(unsigned*last){if(last)*last=__atomic_load_n(&native_screen_target,__ATOMIC_ACQUIRE);return __atomic_load_n(&native_dialog_open_ns,__ATOMIC_ACQUIRE);}
''' +s[a:];needle='for(unsigned j=0;j<3;j++)peek(r[j+1],ids+j,4);';assert needle in s;s=s.replace(needle,needle+'''__atomic_store_n(&native_screen_target,ids[1],__ATOMIC_RELEASE);if(ids[1]==0x2c7&&!__atomic_load_n(&native_dialog_open_ns,__ATOMIC_ACQUIRE)){struct ts t={0};if(!clock_gettime(1,&t)&&t.s>=0&&t.n>=0&&t.n<1000000000L){U at=(U)t.s*1000000000UL+(U)t.n;__atomic_store_n(&native_dialog_open_ns,at,__ATOMIC_RELEASE);}}''');(H/'fx3-preset-context-v3-keys.c').write_text(s)
for old,new in [('fx3-capid-v44','fx3-capid-v45-keys'),('fx3-preset-context-v2-screen','fx3-preset-context-v3-keys')]:
 args=[a.replace(old,new) for a in json.loads((H/(old+'-build.json')).read_text())['args']];p=subprocess.run(args,capture_output=True,text=True);doc={'args':args,'exit':p.returncode,'stderr':p.stderr,'source_sha256':hashlib.sha256((H/(new+'.c')).read_bytes()).hexdigest()};
 if not p.returncode:doc['output_sha256']=hashlib.sha256((H/(new+'.so')).read_bytes()).hexdigest()
 (H/(new+'-build.json')).write_text(json.dumps(doc,indent=2)+'\n');assert not p.returncode,p.stderr
print('AP91 capid45 andpassivescreenv3 compiled')
