/* 411: inject the captured q=0x6110 event at the receive boundary. */
typedef long s64;
extern int dprintf(int,const char*,...);
extern void *dlsym(void*,const char*);
extern void fx6_force_update(void);
static int g_widget_done;
extern void *memcpy(void*,const void*,unsigned long);
static long (*r_rcv)(long,long,long,long,long,long,long,long);
static unsigned char g_cap[0x60];
static unsigned int g_last_id;
static int g_cap_ready, g_injected, g_presenter_done;

int g_fx6_live_active = 0;
static unsigned char g_fake_uipc_pool[256][512];
static unsigned int g_fake_uipc_idx = 0;

static int is_fake_uipc_ptr(unsigned long p) {
    unsigned long base = (unsigned long)&g_fake_uipc_pool[0][0];
    unsigned long end  = base + sizeof(g_fake_uipc_pool);
    return (p >= base && p < end);
}

static void *alloc_fake_uipc_msg(void) {
    unsigned int idx = __sync_fetch_and_add(&g_fake_uipc_idx, 1u) & 0xffu;
    unsigned char *slot = &g_fake_uipc_pool[idx][0];
    for (unsigned int i = 0; i < 512u; i++) slot[i] = 0;
    return (void *)(slot + 0x20);
}

long osal_valloc_msg_wait(long a0,long a1,long a2,long a3,long a4,long a5,long a6,long a7){
    if(g_fx6_live_active){
        if(a1) *(void**)a1 = alloc_fake_uipc_msg();
        return 0;
    }
    static long(*real)(long,long,long,long,long,long,long,long);
    if(!real) real=(long(*)(long,long,long,long,long,long,long,long))dlsym((void*)-1,"osal_valloc_msg_wait");
    return real?real(a0,a1,a2,a3,a4,a5,a6,a7):-1;
}
long u_osal_valloc_msg_wait(long a0,long a1,long a2,long a3,long a4,long a5,long a6,long a7){
    if(g_fx6_live_active){
        if(a1) *(void**)a1 = alloc_fake_uipc_msg();
        return 0;
    }
    static long(*real)(long,long,long,long,long,long,long,long);
    if(!real) real=(long(*)(long,long,long,long,long,long,long,long))dlsym((void*)-1,"u_osal_valloc_msg_wait");
    return real?real(a0,a1,a2,a3,a4,a5,a6,a7):-1;
}
long osal_free_msg(long a0,long a1,long a2,long a3,long a4,long a5,long a6,long a7){
    if(is_fake_uipc_ptr((unsigned long)a0) || is_fake_uipc_ptr((unsigned long)a1)) return 0;
    static long(*real)(long,long,long,long,long,long,long,long);
    if(!real) real=(long(*)(long,long,long,long,long,long,long,long))dlsym((void*)-1,"osal_free_msg");
    return real?real(a0,a1,a2,a3,a4,a5,a6,a7):-1;
}
long u_osal_free_msg(long a0,long a1,long a2,long a3,long a4,long a5,long a6,long a7){
    if(is_fake_uipc_ptr((unsigned long)a0) || is_fake_uipc_ptr((unsigned long)a1)) return 0;
    static long(*real)(long,long,long,long,long,long,long,long);
    if(!real) real=(long(*)(long,long,long,long,long,long,long,long))dlsym((void*)-1,"u_osal_free_msg");
    return real?real(a0,a1,a2,a3,a4,a5,a6,a7):-1;
}

void fx6_inject_set_presenter_done(void){ g_presenter_done=1; dprintf(2,"FX6_INJECT presenter_done\n"); }

long osal_rcv_msg_tmo(long a0,long a1,long a2,long a3,long a4,long a5,long a6,long a7){
    if(!r_rcv) r_rcv=(long(*)(long,long,long,long,long,long,long,long))dlsym((void*)-1,"osal_rcv_msg_tmo");
    void **out=(void**)a1;
    int is6110 = ((unsigned long)a0 & 0xffffUL)==0x6110UL;
    int is_target = ((unsigned long)a0 & 0xffffUL)==0x0030UL;
    if(is_target && out && g_cap_ready && g_presenter_done && g_injected < 200){
        long (*alloc)(long,void*,long,long,long,long,long,long);
        alloc=(long(*)(long,void*,long,long,long,long,long,long))dlsym((void*)-1,"u_osal_valloc_msg_wait");
        void *msg=0; long ar=alloc?alloc(0x8f0139UL,&msg,0x40,0,0,0,0,0):-1;
        dprintf(2,"FX6_INJECT alloc=%ld msg=%p\n",ar,msg);
        if(msg){
            unsigned char *p=(unsigned char*)msg;
            for(int i=0;i<0x28;i++) p[i]=0;
            p[0]=0x20; p[1]=0x00; p[2]=0x00; p[3]=0x00; /* reply type 0x20, status 0 */
            if(g_last_id==0x696){ p[0xc]=1; p[0xd]=0; p[0xe]=0; p[0xf]=0; }
            dprintf(2,"FX6_REPLY_MATCH last=%x flag=%d\n",g_last_id,(g_last_id==0x696));
            dprintf(2,"FX6_INJECT4 zero_reply msg=%p\n",msg);
            *out=msg; g_injected++; if(g_injected==3 && !g_widget_done){ g_widget_done=1; fx6_force_update(); }
            if(g_injected<=10 || (g_injected%20)==0) dprintf(2,"FX6_INJECT5 n=%d zero_reply\n",g_injected);
            return 0;
        }
    }
    if(g_presenter_done){
        static int lg;
        if(lg++<80 || (lg%10)==0) dprintf(2,"FX6_INJECT_RCV n=%d q=%lx tmo=%lx cap=%d inj=%d\n",lg,(unsigned long)a0,(unsigned long)a2,g_cap_ready,g_injected);
        if(is_target && out && g_cap_ready && g_injected < 200){
            long (*alloc)(long,void*,long,long,long,long,long,long);
            alloc=(long(*)(long,void*,long,long,long,long,long,long))dlsym((void*)-1,"u_osal_valloc_msg_wait");
            void *msg=0; long ar=alloc?alloc(0x8f0139UL,&msg,0x40,0,0,0,0,0):-1;
            dprintf(2,"FX6_INJECT2 alloc=%ld msg=%p\n",ar,msg);
            if(msg){
            unsigned char *p=(unsigned char*)msg;
            for(int i=0;i<0x28;i++) p[i]=0;
            p[0]=0x20; p[1]=0x00; p[2]=0x00; p[3]=0x00; /* reply type 0x20, status 0 */
            if(g_last_id==0x696){ p[0xc]=1; p[0xd]=0; p[0xe]=0; p[0xf]=0; }
            dprintf(2,"FX6_REPLY_MATCH last=%x flag=%d\n",g_last_id,(g_last_id==0x696));
            dprintf(2,"FX6_INJECT4 zero_reply msg=%p\n",msg);
            *out=msg; g_injected++; if(g_injected==3 && !g_widget_done){ g_widget_done=1; fx6_force_update(); }
            if(g_injected<=10 || (g_injected%20)==0) dprintf(2,"FX6_INJECT5 n=%d zero_reply\n",g_injected);
            return 0;
        }
        }
    }
    long r=r_rcv?r_rcv(a0,a1,a2,a3,a4,a5,a6,a7):-1;
    if(is6110 && out && !g_cap_ready){
        void *m=*out;
        if(m){ memcpy(g_cap,(unsigned char*)m-0x18,0x40); g_cap_ready=1;
            dprintf(2,"FX6_INJECT_CAP q=%lx pay=%02x%02x\n",(unsigned long)a0,g_cap[0x18],g_cap[0x19]); }
    }
    return r;
}

static unsigned long g_reqn;
static void logreq(const char *tag, unsigned long q, void *p){
    if(!p) return;
    unsigned char *b=(unsigned char*)p;
    unsigned int type=*(unsigned int*)(b+0);
    unsigned int id=*(unsigned int*)(b+4);
    unsigned int par=*(unsigned int*)(b+0x14);
    if(((q & 0xffffUL)==0x003cUL) || q==0x9061003cUL || type==0x20){
        dprintf(2,"FX6_REQ %s n=%lu q=%lx type=%x id=%x par=%x\n",tag,g_reqn,q,type,id,par);
        g_last_id=id;
    }
    g_reqn++;
}
long osal_snd_msg(long a0,long a1,long a2,long a3,long a4,long a5,long a6,long a7){
    if(g_fx6_live_active || is_fake_uipc_ptr((unsigned long)a1) || is_fake_uipc_ptr((unsigned long)a0)){
        if(!is_fake_uipc_ptr((unsigned long)a1) && a1){
            osal_free_msg(a0,a1,0,0,0,0,0,0);
        }
        return 0;
    }
    static long(*real)(long,long,long,long,long,long,long,long);
    if(!real) real=(long(*)(long,long,long,long,long,long,long,long))dlsym((void*)-1,"osal_snd_msg");
    logreq("osal",(unsigned long)a0,(void*)a1);
    return real?real(a0,a1,a2,a3,a4,a5,a6,a7):-1;
}
long u_osal_snd_msg(long a0,long a1,long a2,long a3,long a4,long a5,long a6,long a7){
    if(g_fx6_live_active || is_fake_uipc_ptr((unsigned long)a1) || is_fake_uipc_ptr((unsigned long)a0)){
        if(!is_fake_uipc_ptr((unsigned long)a1) && a1){
            u_osal_free_msg(a0,a1,0,0,0,0,0,0);
        }
        return 0;
    }
    static long(*real)(long,long,long,long,long,long,long,long);
    if(!real) real=(long(*)(long,long,long,long,long,long,long,long))dlsym((void*)-1,"u_osal_snd_msg");
    logreq("uosal",(unsigned long)a0,(void*)a1);
    return real?real(a0,a1,a2,a3,a4,a5,a6,a7):-1;
}
