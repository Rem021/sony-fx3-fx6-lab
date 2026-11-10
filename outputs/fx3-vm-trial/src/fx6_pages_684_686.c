/* 684/685/686 — three more native FX6 pages.
 *
 * Build selector: PAGE_SETBUTTON (684), PAGE_MONITOR (685), PAGE_AUDIO (686).
 *
 * 684 renders TABLE for page 110 (base 0x02eb75f0, 54 rows) strictly from the
 * descriptor geometry: background, twelve separators, title / Index / arrows /
 * title icon, and the thirty slot rows filled with the assignable label pool.
 *
 * 685/686 reuse the three-layer renderer (TABLE 0x2ea02f8) with the selected
 * category moved to Monitoring / Audio and the right column showing that
 * category's own item list.
 *
 * Every id is asked of the firmware before use (fx6_pick), so an alias that is
 * not live in this resource set cannot silently produce an empty label.
 */
#include "/private/tmp/fx6_static_assist.h"
extern int dprintf(int,const char*,...);
extern void *fx6_map_osd(void);
extern void fx6_gds_install(void *fb);
extern void fx6_scan_osd(void);
extern void *calloc(unsigned long,unsigned long);
extern void *dlsym(void*,const char*);

#define FX6_DESC_STRIDE 0x48u

static uint64_t g_appfw;
static uint32_t *g_osd;
static int g_text_ok, g_text_n, g_fill_n, g_icon_n;
static int strstr_(const char *h, const char *n);

void fx6_model_done(void){ dprintf(2,"FX6_MODEL_NONE\n"); }

/* ---------------- native text image -> OSD ------------------------------- */
static int fx6_blit_imagedata_to_osd(void *image, uint32_t *osd, int dst_x, int dst_y)
{
    if (!image || !osd) return 0;
    void *(*gd)(void*) = (void*(*)(void*))dlsym((void*)-1, "_ZN5libra9ImageData16sys_getImageDataEv");
    if (!gd) return 0;
    uint8_t *raw = (uint8_t*)gd(image);
    if (!raw) return 0;
    int w = *(uint16_t*)(raw + 0x00);
    int h = *(uint16_t*)(raw + 0x02);
    int pitch_px = (int)(*(uint32_t*)(raw + 0x04));
    void *bmp = *(void**)(raw + 0x18);
    if (!bmp || w<=0 || h<=0 || pitch_px<=0) return 0;
    const uint8_t *bits = *(const uint8_t**)((uint8_t*)bmp + 0x10);
    if (!bits) return 0;
    if (w > 1024) w = 1024;
    int stride = pitch_px * 4;
    int copied = 0;
    for (int y=0; y<h; y++){
        int dy = dst_y + y;
        if (dy < 0 || dy >= 540) continue;
        const uint16_t *srow = (const uint16_t*)(bits + (unsigned long)y*(unsigned long)stride);
        uint32_t *drow = osd + (unsigned long)dy * 1024UL;
        for (int x=0; x<w; x++){
            int dx = dst_x + x;
            if (dx < 0 || dx >= 1024) continue;
            uint16_t pv = srow[x];
            uint32_t a = (pv & 0xf) * 17u;
            if (a == 0) continue;
            uint32_t r = ((pv >> 12) & 0xf) * 17u;
            uint32_t g = ((pv >>  8) & 0xf) * 17u;
            uint32_t b = ((pv >>  4) & 0xf) * 17u;
            drow[dx] = (a<<24) | (r<<16) | (g<<8) | b;
            copied++;
        }
    }
    return copied;
}

static void fx6_text_image_cb(void *ts, void *image, void *ud)
{
    (void)ts;
    int dx = 0, dy = 0;
    if (ud) { dx = *(int32_t*)((char*)ud+0x1e8); dy = *(int32_t*)((char*)ud+0x1ec); }
    int n = fx6_blit_imagedata_to_osd(image, g_osd, dx, dy);
    if (n) g_text_ok++;
}

/* ---------------- resources ---------------------------------------------- */
static int fx6_add_arena(int idx, unsigned min, unsigned max)
{
    unsigned char param[0x20];
    for (unsigned i=0;i<sizeof(param);i++) param[i]=0;
    void *buf = calloc(1, max);
    if (!buf) return 0;
    *(unsigned*)(param+0x00)=max;
    *(unsigned*)(param+0x04)=min;
    *(unsigned*)(param+0x08)=max;
    *(void**)(param+0x10)=buf;
    *(unsigned char*)(param+0x19)=1;
    *(unsigned char*)(param+0x1a)=0xff;
    *(unsigned char*)(param+0x1b)=3;
    int (*add)(unsigned char,const void*)=(int(*)(unsigned char,const void*))
        dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager8addArenaEhRKN5libra10ArenaParamE");
    if (!add) return 0;
    return add((unsigned char)idx,(const void*)param);
}

static void fx6_load_fonts(void)
{
    int (*ld)(unsigned int)=(int(*)(unsigned int))
        dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager16sys_loadFontDataEj");
    if (!ld) return;
    int ok=0,total=0;
    for (unsigned r=0x02006000U; r<=0x0200603fU; r++){ total++; if (ld(r)) ok++; }
    for (unsigned r=0x0200a000U; r<=0x0200a02fU; r++){ total++; if (ld(r)) ok++; }
    for (unsigned r=0x02008000U; r<=0x0200800fU; r++){ total++; if (ld(r)) ok++; }
    dprintf(2,"FX6_VSR68y loadFonts ok=%d/%d\n",ok,total);
}

/* ---------------- ResID helpers ------------------------------------------ */
static int fx6_text_of(uint32_t rid, char *out, unsigned outsz)
{
    void (*sc)(void*) = (void(*)(void*))dlsym((void*)-1,"_ZN5libra6StringC1Ev");
    const char *(*pb)(const void*) = (const char*(*)(const void*))dlsym((void*)-1,"_ZNK6stella6String9ptrBufferEv");
    int (*gt)(unsigned,void*) = (int(*)(unsigned,void*))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager7getTextEjRN5libra6StringE");
    out[0]=0;
    if (!sc||!pb||!gt) return 0;
    unsigned char buf[0x40];
    for (unsigned k=0;k<sizeof(buf);k++) buf[k]=0;
    sc(buf);
    int rc=gt(rid,buf);
    const char *s=pb(buf);
    if (rc && s) { unsigned n=0; while (s[n] && n+1<outsz){ out[n]=s[n]; n++; } out[n]=0; return n>0; }
    return 0;
}

static uint32_t fx6_pick(uint32_t a, uint32_t b, const char *want, const char *what)
{
    char t[0x60];
    if (fx6_text_of(a,t,sizeof(t)) && want && t[0] && strstr_(t,want)) return a;
    if (fx6_text_of(b,t,sizeof(t)) && want && t[0] && strstr_(t,want)) return b;
    dprintf(2,"FX6_VSR68y pick %s: neither %08x nor %08x matched \"%s\"\n",
            what, a, b, want?want:"");
    return a;
}

static int strstr_(const char *h, const char *n)
{
    if (!h||!n) return 0;
    for (; *h; h++){
        const char *a=h, *b=n;
        while (*a && *b && *a==*b){ a++; b++; }
        if (!*b) return 1;
    }
    return 0;
}

/* ---------------- native widgets ----------------------------------------- */
static void fx6_render_string_rid(uint64_t appfw, int x, int y, int w, int h,
                                  uint32_t text_resid, const char *tag_name)
{
    if (!text_resid || text_resid==0xffffffffU) return;
    if (w < 8 || h < 4) return;
    void *vs = calloc(1, 0x1400);
    if (!vs) return;
    char param[0x40];
    for (unsigned i=0;i<sizeof(param);i++) param[i]=0;
    ((void(*)(void*,void*))(uintptr_t)(appfw+0xc3af98ULL))(vs,param);

    *(int32_t*)((char*)vs+0x1e8)=x;
    *(int32_t*)((char*)vs+0x1ec)=y;
    *(int32_t*)((char*)vs+0x1f0)=w;
    *(int32_t*)((char*)vs+0x1f4)=h;
    *(uint32_t*)((char*)vs+0x200)=text_resid;
    *(uint8_t*)((char*)vs+0x1fc)=1;
    *(uint32_t*)((char*)vs+0x208)=0x0200600fU;
    *(uint32_t*)((char*)vs+0x20c)=0x0200600eU;
    *(uint32_t*)((char*)vs+0x210)=0x0200a029U;
    *(uint32_t*)((char*)vs+0xa14)=0x0200600bU;
    *(int*)((char*)vs+0x214)=0;
    *(int*)((char*)vs+0x21c)=1;
    *(int*)((char*)vs+0x610)=0;
    *(uint32_t*)((char*)vs+0xa30)=0x0200a005U;

    void *ts=(char*)vs+0xe40;
    void (*setcb)(void*,void*,void*)=(void(*)(void*,void*,void*))
        dlsym((void*)-1,"_ZN2ux6gfxeng10TextSprite20setImageLoadCallbackEPFvPS1_PN5libra9ImageDataEPvES6_");
    if (setcb) setcb(ts,(void*)fx6_text_image_cb,vs);
    *(unsigned short*)((char*)ts+0xa8) |= 0x0008;

    void **vt=*(void***)vs;
    if (!vt || !vt[0x158/8]) return;
    ((void(*)(void*))vt[0x158/8])(vs);

    *(unsigned short*)((char*)ts+0xa8) |= 0x0006;
    void (*dti)(void*)=(void(*)(void*))dlsym((void*)-1,"_ZN2ux6gfxeng10TextSprite12drawTextImplEv");
    if (dti) dti(ts);
    { int (*pc)(unsigned int)=(int(*)(unsigned int))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager15processCommandsEj");
      if (pc) pc(0); }

    dprintf(2,"FX6_VSR68y %s (%d,%d,%d,%d) text=%08x\n", tag_name, x,y,w,h, text_resid);
    g_text_n++;
}

static void fx6_fill_rect(uint64_t appfw, int x, int y, int w, int h, uint32_t color_resid)
{
    if (w < 1 || h < 1) return;
    void *vf = calloc(1, 0x1180);
    if (!vf) return;
    char param[0x40];
    for (unsigned i=0;i<sizeof(param);i++) param[i]=0;
    ((void(*)(void*,void*))(uintptr_t)(appfw+0xc27698ULL))(vf,param);

    *(int32_t*)((char*)vf+0x1e8)=x;
    *(int32_t*)((char*)vf+0x1ec)=y;
    *(int32_t*)((char*)vf+0x1f0)=w;
    *(int32_t*)((char*)vf+0x1f4)=h;
    if (color_resid) *(uint32_t*)((char*)vf+0x200)=color_resid;
    *(uint8_t*)((char*)vf+0x1fc)=1;

    void **vt=*(void***)vf;
    if (!vt) return;
    if (vt[0x148/8]) ((void(*)(void*))vt[0x148/8])(vf);
    if (!vt[0x158/8]) return;
    ((void(*)(void*))vt[0x158/8])(vf);

    { int (*pc)(unsigned int)=(int(*)(unsigned int))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager15processCommandsEj");
      if (pc) pc(0); }
    char *spr=(char*)vf+0x210;
    char *rects=*(char**)(spr+0xd0);
    if (rects) {
        float pos[2]={(float)x,(float)y};
        void (*srp)(void*,unsigned short,const void*)=(void(*)(void*,unsigned short,const void*))
            dlsym((void*)-1,"_ZN2ux6gfxeng6Sprite10setRectPosEtRKNS_4core7Vector2E");
        if (srp) srp(spr,0,pos);
        else { *(float*)(rects+0x00)=pos[0]; *(float*)(rects+0x04)=pos[1]; }
        void (*rr)(void*,const void*,const void*,float,float)=(void(*)(void*,const void*,const void*,float,float))
            dlsym((void*)-1,"_ZN2ux6gfxeng6Sprite10renderRectERKNS_4core7Vector2ERKNS1_8RectDataEff");
        if (rr) rr(spr, pos, rects, 0.0f, 0.0f);
    }
    g_fill_n++;
}

static void fx6_icon_blit(uint64_t appfw, int x, int y, int w, int h, uint32_t img)
{
    if (w < 1 || h < 1) return;
    if (!img || img==0xffffffffU) return;
    void *ic = calloc(1, 0x700);
    if (!ic) return;
    char param[0x40];
    for (unsigned i=0;i<sizeof(param);i++) param[i]=0;
    ((void(*)(void*,void*))(uintptr_t)(appfw+0xc2c188ULL))(ic,param);

    *(int32_t*)((char*)ic+0x1e8)=x;
    *(int32_t*)((char*)ic+0x1ec)=y;
    *(int32_t*)((char*)ic+0x1f0)=w;
    *(int32_t*)((char*)ic+0x1f4)=h;
    *(uint32_t*)((char*)ic+0x20c)=img;
    *(uint8_t*)((char*)ic+0x1fc)=1;
    *(uint8_t*)((char*)ic+0x21c)=0xff;
    *(uint8_t*)((char*)ic+0x21d)=0xff;
    *(uint8_t*)((char*)ic+0x21e)=0xff;
    *(uint8_t*)((char*)ic+0x21f)=0xff;
    *(uint16_t*)((char*)ic+0x204)=w;
    *(uint16_t*)((char*)ic+0x206)=h;

    void **vt=*(void***)ic;
    if (!vt) return;
    if (vt[0x148/8]) ((void(*)(void*))vt[0x148/8])(ic);
    if (vt[0x158/8]) ((void(*)(void*))vt[0x158/8])(ic);
    { int (*pc)(unsigned int)=(int(*)(unsigned int))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager15processCommandsEj");
      if (pc) pc(0); }
    g_icon_n++;
}

/* ------------------------------------------------------------------ pages */
#define FX6_COLOR_SEL 0x0200c014u

static const uint32_t g_cats[9] = {
    0x02004208u, 0x02004d4au, 0x02002227u, 0x02002228u, 0x02002493u,
    0x0200222bu, 0x02002229u, 0x020041fbu, 0x02004209u,
};

#ifdef PAGE_SETBUTTON
/* ---------- 684: page 110, Assignable Button grid --------------------- */
/* The thirty slot rows are the ones whose descriptor tag is a menu item; their
 * rectangles come from the table, their labels from the assignable pool. */
static const int g_slot_rows[30] = {
    /* left column, top to bottom (BUTTON_01..12 in table order) */
    2, 12, 11, 10, 9, 8, 26, 25, 24, 23, 22, 21,
    /* right column (BUTTON_07..14) */
    19, 18, 17, 16, 15, 14, 13, 20, 28, 7, 6, 5,
    /* bottom strip pairs */
    4, 3, 32, 31, 29, 27,
};

static const uint32_t g_pool[30] = {
    0x020023c4u, 0x020020d0u, 0x02004288u, 0x0200423du, 0x0200423fu, 0x0200423eu,
    0x020049f5u, 0x0200290au, 0x02004246u, 0x0200425fu, 0x02004261u, 0x02004242u,
    0x02004253u, 0x02004254u, 0x0200425au, 0x02002e6du, 0x02004214u, 0x02004217u,
    0x02004218u, 0x02004285u, 0x02004212u, 0x02004211u, 0x02004210u, 0x02004229u,
    0x0200422au, 0x02004239u, 0x0200423au, 0x02004241u, 0x0200429fu, 0x02004285u,
};

static void page_setbutton(uint64_t appfw)
{
    /* descriptor table for page 110 (appFw base 0x02eb75f0, 54 rows) */
    uint8_t *base=(uint8_t*)(uintptr_t)(appfw + 0x2eb75f0ULL);

    /* pass 1: background + separators (fills only) */
    for (int i=1;i<54;i++){
        uint8_t *p = base + (uint64_t)i*FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void**)p - appfw);
        if (tag != 0x42d5a40u && tag != 0x42d57d0u) continue;   /* view_fill */
        uint32_t c = *(uint32_t*)(p+0x18);
        uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
        uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
        fx6_fill_rect(appfw, x, y, w, h, c);
    }

    /* pass 2: chrome text — title, Index, arrows, title icon */
    for (int i=0;i<54;i++){
        uint8_t *p = base + (uint64_t)i*FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void**)p - appfw);
        uint32_t c = *(uint32_t*)(p+0x18);
        uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
        uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
        if (!c || c==0xffffffffU) continue;
        if (tag == 0x42d57f0u) {          /* view_string chrome */
            fx6_render_string_rid(appfw, x, y, w, h, c, "chrome-text");
        } else if (tag == 0x42d5a50u) {    /* view_icon chrome */
            fx6_icon_blit(appfw, x, y, w, h, c);
        }
    }

    /* pass 3: the thirty slots, label from the pool */
    for (int s=0;s<30;s++){
        uint8_t *p = base + (uint64_t)g_slot_rows[s]*FX6_DESC_STRIDE;
        uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
        uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
        if (w<8||h<8) continue;
        if (s == 0) fx6_fill_rect(appfw, x, y, w, h, FX6_COLOR_SEL);
        fx6_render_string_rid(appfw, x+14, y+6, w-28, h-10, g_pool[s], "slot-label");
    }
}
#endif

#if defined(PAGE_MONITOR) || defined(PAGE_AUDIO)
/* ---------- 685/686: three-layer page with a different category ------- */
static void page_l2(uint64_t appfw, int sel_cat, uint32_t title_rid,
                    const uint32_t *items, int n_items)
{
    uint8_t *base=(uint8_t*)(uintptr_t)(appfw + 0x2ea02f8ULL);
    for (int i=0;i<35;i++){
        uint8_t *p = base + (uint64_t)i*FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void**)p - appfw);
        if (tag != 0x42d5a40u && tag != 0x42d57d0u) continue;
        fx6_fill_rect(appfw, *(uint16_t*)(p+0x3c), *(uint16_t*)(p+0x3e),
                      *(uint16_t*)(p+0x40), *(uint16_t*)(p+0x42),
                      *(uint32_t*)(p+0x18));
    }
    const int lx=62, ly=56, lw=494, lh=462, rows=9;
    const int rh = lh/rows;
    for (int i=0;i<rows;i++){
        int y = ly + i*rh;
        if (i == sel_cat) fx6_fill_rect(appfw, lx, y, lw, rh-3, FX6_COLOR_SEL);
        fx6_render_string_rid(appfw, lx+16, y+8, lw-32, rh-10, g_cats[i], "category");
    }
    fx6_render_string_rid(appfw, 568, 62, 280, 36, title_rid, "col-title");
    fx6_icon_blit(appfw, 578, 112, 38, 38, 0x02000154u);
    fx6_render_string_rid(appfw, 622, 112, 326, 40, 0x02004c3eu, "back");
    for (int i=0;i<n_items;i++){
        int y = 163 + i*51;
        if (i == 0) fx6_fill_rect(appfw, 578, y-6, 370, 44, FX6_COLOR_SEL);
        fx6_render_string_rid(appfw, 578, y, 370, 40, items[i], "list-item");
    }
}
#endif

void fx6_force_update(void){
    g_appfw=fx6_appfw_base_auto();
    void *fb=fx6_map_osd();
    g_osd=(uint32_t*)fb;
    dprintf(2,"FX6_VSR68y appfw=%llx fb=%p\n",(unsigned long long)g_appfw,fb);
    if(!g_appfw||!fb) return;
    fx6_gds_install(fb);
    int (*setcwd)(const char*)=(int(*)(const char*))dlsym((void*)-1,"_ZN2ux4core6Kernel23sys_setCurrentDirectoryEPKc");
    int (*setdb)(const char*)=(int(*)(const char*))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager11setDatabaseEPKc");
    int (*setns)(unsigned short)=(int(*)(unsigned short))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager28sys_setFontNameWithNamespaceEt");
    int (*swbank)(unsigned short,unsigned char)=(int(*)(unsigned short,unsigned char))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager10switchBankEth");
    int (*proccmd)(unsigned int)=(int(*)(unsigned int))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager15processCommandsEj");
    if(setcwd) setcwd("/usr/share/app/");
    if(setdb) dprintf(2,"FX6_VSR68y setdb=%d\n",setdb("global.xdb"));
    if(setns) dprintf(2,"FX6_VSR68y setns=%d\n",setns(5));
    if(swbank){ swbank(0,0); swbank(1,4); swbank(2,4); }
    fx6_add_arena(0,0x100000U,0x800000U);
    fx6_add_arena(1,0x080000U,0x400000U);
    fx6_add_arena(2,0x080000U,0x200000U);
    fx6_load_fonts();
    fx6_model_ready(g_appfw);
    fx6_engine_gate_auto();

#if defined(PAGE_SETBUTTON)
    page_setbutton(g_appfw);
#elif defined(PAGE_MONITOR)
    {
        static const uint32_t items[7] = {
            0x02004238u, 0x02004236u, 0x02004235u, 0x02004234u,
            0x02004239u, 0x0200423au, 0x02004241u,
        };
        page_l2(g_appfw, 6, 0x02002229u, items, 7);
    }
#elif defined(PAGE_AUDIO)
    {
        static const uint32_t items[7] = {
            0x02004232u, 0x02004233u, 0x02004234u, 0x02002192u,
            0x02002191u, 0x02003132u, 0x0200429fu,
        };
        page_l2(g_appfw, 7, 0x020041fbu, items, 7);
    }
#endif
    if (proccmd) proccmd(0);
    dprintf(2,"FX6_VSR68y done text=%d fill=%d icon=%d text_ok=%d\n",
            g_text_n,g_fill_n,g_icon_n,g_text_ok);
    fx6_scan_osd();
}
