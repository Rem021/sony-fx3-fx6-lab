from pathlib import Path
import json,hashlib,subprocess,plistlib
R=Path(__file__).resolve().parent;H=R/'helpers'
assert plistlib.loads(subprocess.check_output(['diskutil','info','-plist','/Volumes/KAFU2T']))['VolumeUUID']=='F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B'
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
header=r'''
/* AP97r2 passive observation: caller owns sync request through return; never writes it. */
static void date97_point(U id,U pc,U *r){
 unsigned char fc[2]={255,255},at0=255,at19=255;W dc=0xffffffffU,dn=0xffffffffU;
 int fr=peek(app_base+0x8365c90,fc,2),cr=peek(app_base+0x8227358,&dc,4),nr=peek(app_base+0x822735c,&dn,4);
 int p0=peek(r[0],&at0,1),p19=peek(r[19],&at19,1);
 dprintf(2,"FX3_DATE97_POINT id=%lu pc=%#lx tid=%ld w0=%d w1=%u x19=%#lx x24=%#lx x25=%#lx force_read=%d force_current=%u force_next=%u date_current_read=%d date_current=%u date_next_read=%d date_next=%u p0_read=%d p0_byte=%u p19_read=%d p19_byte=%u passive=1\n",id,pc,syscall(178),(int)(W)r[0],(W)r[1],r[19],r[24],r[25],fr,fc[0],fc[1],cr,dc,nr,dn,p0,at0,p19,at19);
}
static U date97_events;
static int date97_sync(int (*fn)(W,void*),W (*sizefn)(void*),W dst,void *request){
 int saved=*__errno_location();
 if(dst!=0x80900141U||!request){*__errno_location()=saved;return fn(dst,request);}
 U event=__atomic_add_fetch(&date97_events,1,__ATOMIC_RELAXED);W n=sizefn?sizefn(request):0;unsigned char before[4096],after[4096];char hex[8193];const char *digits="0123456789abcdef";
 int cap=event<=64&&n>0&&n<=4096,br=cap&&peek((U)request,before,n);
 if(br){for(W i=0;i<n;i++){hex[2*i]=digits[before[i]>>4];hex[2*i+1]=digits[before[i]&15];}hex[2*n]=0;dprintf(2,"FX3_DATE97_SYNC phase=before event=%lu tid=%ld destination=%#x pointer=%p bytes=%u raw=%s original_sync_delegated=1 caller_owns_until_return=1\n",event,syscall(178),dst,request,n,hex);}
 else dprintf(2,"FX3_DATE97_SYNC phase=before event=%lu bytes=%u captured=0 bound=4096 limit=64\n",event,n);
 *__errno_location()=saved;int rc=fn(dst,request);int result_errno=*__errno_location();int ar=cap&&peek((U)request,after,n);
 if(ar){for(W i=0;i<n;i++){hex[2*i]=digits[after[i]>>4];hex[2*i+1]=digits[after[i]&15];}hex[2*n]=0;dprintf(2,"FX3_DATE97_SYNC phase=after event=%lu tid=%ld destination=%#x pointer=%p bytes=%u result=%d errno=%d raw=%s body_unmodified_by_observer=1\n",event,syscall(178),dst,request,n,rc,result_errno,hex);}
 else dprintf(2,"FX3_DATE97_SYNC phase=after event=%lu result=%d errno=%d captured=0\n",event,rc,result_errno);
 *__errno_location()=result_errno;return rc;
}
'''
p=H/'fx3-date-observe97r2.h';assert not p.exists();p.write_text(header)
s=(H/'fx3-preset-context-v2-screen.c').read_text();s=s.replace('__attribute__((visibility("hidden"))) void fx3_display_event',' #include "fx3-date-observe97r2.h"\n__attribute__((visibility("hidden"))) void fx3_display_event',1)
s=s.replace(' *__errno_location()=saved;\n}', ' if(id>=80&&id<=87)date97_point(id,c->pc-app_base,r);\n *__errno_location()=saved;\n}',1)
points=[(0x2d7e6f4,0x2a0003f3),(0x2d7e73c,0x39000300),(0x2d7e744,0x52821300),(0x2a69a84,0x39400001),(0x2ab9028,0xa9be7bfd),(0x2b23730,0x940e7180),(0x2ebfd5c,0xaa1303e2),(0x2ebfd70,0xaa1303e1)]
# Preserve six existing points and validate all 14 words before any installation.
s=s.replace('U addresses[6]={','U addresses[14]={').replace('app_base+0x218fff4};W words[6]={','app_base+0x218fff4,'+','.join('app_base+'+hex(a) for a,w in points)+'};W words[14]={').replace('0xf834dae0};U ids[6]={24,37,28,32,40,41};','0xf834dae0,'+','.join(hex(w) for a,w in points)+'};U ids[14]={24,37,28,32,40,41,80,81,82,83,84,85,86,87};')
s=s.replace('i<6','i<14').replace('points=6 original0404entry_and_RET=1','points=14 passive_date_force_backup=8 original0404entry_and_RET=1')
s+='\nint osal_snd_sync_msg(W dst,void *request){int saved=*__errno_location();int (*fn)(W,void*)=dlsym((void*)-1,"osal_snd_sync_msg");W (*sizefn)(void*)=dlsym((void*)-1,"osal_msg_size");if(!fn)__builtin_trap();*__errno_location()=saved;return date97_sync(fn,sizefn,dst,request);}\n'
assert s.count('date97_point(id,c->pc-app_base,r)')==1 and 'i<6' not in s
p=H/'fx3-preset-context-v3-date97.c';assert not p.exists();p.write_text(s)
# Original point-by-point provenance, including synchronous call ownership disassembly.
proof=json.loads((R/'ap97r2-date-observer-original-points.json').read_text());flat={x['va']:x for rows in proof.values() for x in rows}
for a,w in points:assert flat[hex(a)]['raw']==w.to_bytes(4,'little').hex()
for old,new,replace in [('fx3-preset-context-v2-screen','fx3-preset-context-v3-date97',{}),('fx3-gpe-observe-v19r4-parent-source','fx3-gpe-observe-v20-const-alpha97',{'fx3-gpe-backend-v5.c':'fx3-gpe-backend-v6.c'})]:
 b=json.loads((H/(old+'-build.json')).read_text());args=[a.replace(old,new) for a in b['args']];args=[next((a.replace(k,v) for k,v in replace.items() if k in a),a) for a in args]
 proc=subprocess.run(args,capture_output=True,text=True);(H/(new+'-build.log')).write_text(proc.stdout+proc.stderr);assert proc.returncode==0,proc.stderr
 record={'args':args,'exit':0,'authority':'msg_155b0cf9b5b7','source_sha256':sha(H/(new+'.c')),'output_sha256':sha(H/(new+'.so')),'original_source_sha256':sha(H/(old+'.c')),'changed_scope':'bounded constant-alpha straight-over approximation only' if replace else '8 original instruction verified passive observations plus original sync request before/after capture; preserve GPR/SIMD/NZCV/errno; no model/Backup writes','extra_sources':{str(q):sha(q) for q in ([H/'fx3-gpe-backend-v6.c',H/'fx3-gpe-backend-v6.h'] if replace else [H/'fx3-date-observe97r2.h',H/'fx3-display-probes-v1.S',R/'ap97r2-date-observer-original-points.json'])}}
 (H/(new+'-build.json')).write_text(json.dumps(record,indent=2)+'\n')
print('OBSERVERS97R2_CROSS_BUILD_PASS')
