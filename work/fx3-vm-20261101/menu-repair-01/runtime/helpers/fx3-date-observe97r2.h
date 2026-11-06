
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
