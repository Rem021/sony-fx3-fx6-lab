/* 681/682/683 — three native FX6 pages rendered from appFw's own tables.
 *
 * Build selector: PAGE_PROJECT (681), PAGE_CENTER (682), PAGE_SETTING (683).
 *
 * Every rectangle, colour and caption below comes from one of:
 *   - the firmware descriptor tables (TABLE 0x2ea02f8 / 0x2eaf208 / 0x2ea3e50), or
 *   - appFw .rodata ResID tables resolved at runtime through the native
 *     ResourceManager (mapA 0x226a6c0, the option tables the static line decoded).
 *
 * Where two ResIDs are quoted for the same label (the static line and the mapA
 * slot table disagree on a few ids), fx6_pick() asks the firmware which one
 * actually resolves to the expected text and uses that. No text is authored here.
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
    dprintf(2,"FX6_VSR68x text blit n=%d at %d,%d\n",n,dx,dy);
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
    dprintf(2,"FX6_VSR68x loadFonts ok=%d/%d\n",ok,total);
}

static int strstr_(const char *h, const char *n);

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

/* Pick the id that the firmware actually resolves to `want`.
 * Both ids come from appFw tables; this only decides which alias is live. */
static uint32_t fx6_pick(uint32_t a, uint32_t b, const char *want, const char *what)
{
    char t[0x60];
    if (fx6_text_of(a,t,sizeof(t)) && want && t[0] && strstr_(t,want)) return a;
    if (fx6_text_of(b,t,sizeof(t)) && want && t[0] && strstr_(t,want)) return b;
    dprintf(2,"FX6_VSR68x pick %s: neither %08x nor %08x matched \"%s\" (a=\"%s\")\n",
            what, a, b, want?want:"", t);
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

    dprintf(2,"FX6_VSR68x %s (%d,%d,%d,%d) text=%08x\n", tag_name, x,y,w,h, text_resid);
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

static int fx6_tag_kind(uint64_t appfw, void *proto)
{
    if (!proto) return 0;
    uint64_t tag = (uint64_t)(uintptr_t)proto - appfw;
    switch ((uint32_t)tag) {
    case 0x42d57f0u: case 0x42d59a0u: return 1;
    case 0x42d5a40u: case 0x42d57d0u: return 2;
    case 0x42d58d0u:                 return 3;
    case 0x42d5a50u: case 0x42d5800u: case 0x42d5930u: return 4;
    default: return 0;
    }
}

static void fx6_border(uint64_t appfw, int x, int y, int w, int h, uint32_t color_resid)
{
    if (w < 3 || h < 3) return;
    fx6_fill_rect(appfw, x,     y,     w, 1, color_resid);
    fx6_fill_rect(appfw, x,     y+h-1, w, 1, color_resid);
    fx6_fill_rect(appfw, x,     y,     1, h, color_resid);
    fx6_fill_rect(appfw, x+w-1, y,     1, h, color_resid);
}

/* ------------------------------------------------------------------ pages */
#define FX6_COLOR_SEL 0x0200c014u

/* nine level-1 categories, in the camera's order (mapA slot ids) */
static const uint32_t g_cats[9] = {
    0x02004208u, 0x02004d4au, 0x02002227u, 0x02002228u, 0x02002493u,
    0x0200222bu, 0x02002229u, 0x020041fbu, 0x02004209u,
};

#if defined(PAGE_PROJECT) || defined(PAGE_CENTER)
/* ---------- 681: level-1 column + a level-2 option page ---------------- */
static void page_project(uint64_t appfw)
{
    /* native fills of the three-layer table first */
    uint8_t *base=(uint8_t*)(uintptr_t)(appfw + 0x2ea02f8ULL);
    for (int i=0;i<35;i++){
        uint8_t *p = base + (uint64_t)i*FX6_DESC_STRIDE;
        if (fx6_tag_kind(appfw, *(void**)p) == 2) {
            uint32_t c = *(uint32_t*)(p+0x18);
            uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
            uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
            fx6_fill_rect(appfw, x, y, w, h, c);
        }
    }

    /* left column: nine categories, Project selected (index 3) */
    const int lx=62, ly=56, lw=494, lh=462, rows=9;
    const int rh = lh/rows;
    for (int i=0;i<rows;i++){
        int y = ly + i*rh;
        if (i == 3) { fx6_fill_rect(appfw, lx, y, lw, rh-3, FX6_COLOR_SEL); }
        fx6_render_string_rid(appfw, lx+16, y+8, lw-32, rh-10, g_cats[i], "category");
    }

    /* right column: title / back / five rec-format options */
    uint32_t recfmt = fx6_pick(0x0200425fu, 0x020022d2u, "Rec Format", "Rec Format title");
    fx6_render_string_rid(appfw, 568, 62, 280, 36, recfmt, "col-title");
    fx6_icon_blit(appfw, 578, 112, 38, 38, 0x02000154u);
    fx6_render_string_rid(appfw, 622, 112, 326, 40, 0x02004c3eu, "back");

    static const uint32_t opts[5] = {
        0x02004987u, 0x02004989u, 0x0200498bu, 0x0200498du, 0x0200498fu,
    };
    for (int i=0;i<5;i++){
        int y = 163 + i*51;
        if (i == 0) fx6_fill_rect(appfw, 578, y-6, 370, 44, FX6_COLOR_SEL);
        fx6_render_string_rid(appfw, 578, y, 370, 40, opts[i], "rec-format");
    }
}
#endif

#ifdef PAGE_CENTER
/* ---------- 682: setting centre page, TABLE 0x2eaf208 (17 rows) -------- */
static void page_center(uint64_t appfw)
{
    uint8_t *base=(uint8_t*)(uintptr_t)(appfw + 0x2eaf208ULL);
    /* rows 1..10 mix fills and view_strings: only the fills carry a colour,
     * a string row with +0x18 == 0 would paint a white bar if filled. */
    for (int i=1;i<=10;i++){
        uint8_t *p = base + (uint64_t)i*FX6_DESC_STRIDE;
        if (fx6_tag_kind(appfw, *(void**)p) != 2) continue;
        uint32_t c = *(uint32_t*)(p+0x18);
        uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
        uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
        if (w<1||h<1) continue;
        fx6_fill_rect(appfw, x, y, w, h, c);
    }
    /* 11..16 are the six outer cells: border + title + value each */
    for (int i=11;i<=16;i++){
        uint8_t *p = base + (uint64_t)i*FX6_DESC_STRIDE;
        uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
        uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
        if (w<8||h<8) continue;
        fx6_border(appfw, x, y, w, h, 0x0200c00eu);
    }
    /* centre strip: title + value */
    {
        uint8_t *t = base + 4*FX6_DESC_STRIDE;   /* No7_CENTER_TITLE */
        uint8_t *v = base + 3*FX6_DESC_STRIDE;   /* No8_CENTER_VALUE */
        uint32_t look  = fx6_pick(0x020029f8u, 0x02002feau, "Look", "centre title");
        uint32_t value = 0x02002464u;            /* S-Cinetone */
        uint16_t tx=*(uint16_t*)(t+0x3c), ty=*(uint16_t*)(t+0x3e);
        uint16_t tw=*(uint16_t*)(t+0x40), th=*(uint16_t*)(t+0x42);
        uint16_t vx=*(uint16_t*)(v+0x3c), vy=*(uint16_t*)(v+0x3e);
        uint16_t vw=*(uint16_t*)(v+0x40), vh=*(uint16_t*)(v+0x42);
        fx6_render_string_rid(appfw, tx, ty, tw, th, look,  "centre-title");
        fx6_render_string_rid(appfw, vx, vy, vw, vh, value, "centre-value");
    }
    /* six outer cells: title above value, both inside the cell rect */
    {
        static const uint32_t titles[6] = {
            0x02005082u, 0x020050e8u, 0x02004c32u,
            0x02004288u, 0x02005689u, 0x020023f8u,
        };
        static const uint32_t values[6] = {
            0x020030ceu, 0x02002fe1u, 0x02005459u,
            0x020054fdu, 0x02002934u, 0x02002464u,
        };
        for (int i=11;i<=16;i++){
            uint8_t *p = base + (uint64_t)i*FX6_DESC_STRIDE;
            uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
            uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
            if (w<8||h<8) continue;
            int c = i-11;
            fx6_fill_rect(appfw, x+1, y+1, w-2, h-2, 0x0200c008u);
            fx6_render_string_rid(appfw, x+8, y+6, w-16, 30, titles[c], "cell-title");
            fx6_render_string_rid(appfw, x+8, y+40, w-16, h-46, values[c], "cell-value");
        }
    }
}
#endif

#ifdef PAGE_SETTING
/* ---------- 683: setting main page, TABLE 0x2ea3e50 ------------------- */
static void page_setting(uint64_t appfw)
{
    uint8_t *base=(uint8_t*)(uintptr_t)(appfw + 0x2ea3e50ULL);
    /* native fills (there are none on this page, but keep the code uniform) */
    for (int i=0;i<10;i++){
        uint8_t *p = base + (uint64_t)i*FX6_DESC_STRIDE;
        if (fx6_tag_kind(appfw, *(void**)p) == 2) {
            fx6_fill_rect(appfw, *(uint16_t*)(p+0x3c), *(uint16_t*)(p+0x3e),
                          *(uint16_t*)(p+0x40), *(uint16_t*)(p+0x42),
                          *(uint32_t*)(p+0x18));
        }
    }
    /* left list: eight level-1 categories inside No4_SETTING_LIST_MAIN */
    const int lx=96, ly=72, lw=402, lh=432, rows=8;
    const int rh = lh/rows;                     /* 54 */
    for (int i=0;i<rows;i++){
        int y = ly + i*rh;
        if (i == 2) { fx6_fill_rect(appfw, lx, y, lw, rh-3, FX6_COLOR_SEL); }
        fx6_render_string_rid(appfw, lx+20, y+10, lw-40, rh-14, g_cats[i], "setting-cat");
    }
    /* right side: main string / item / value */
    fx6_render_string_rid(appfw, 519,  95, 305, 32, 0x02002227u, "main-string");
    fx6_render_string_rid(appfw, 534, 158, 290, 32, 0x020023f8u, "setting-item");
    fx6_render_string_rid(appfw, 534, 193, 290, 32, 0x02002464u, "setting-value");
    /* four buttons */
    {
        uint32_t set = fx6_pick(0x020023dau, 0x020047a4u, "Set", "button label");
        static const int bx[4]={654,398,654,398}, by[4]={425,425,80,80};
        for (int i=0;i<4;i++)
            fx6_render_string_rid(appfw, bx[i]+30, by[i]+24, 110, 30, set, "button");
    }
}
#endif

void fx6_force_update(void){
    g_appfw=fx6_appfw_base_auto();
    void *fb=fx6_map_osd();
    g_osd=(uint32_t*)fb;
    dprintf(2,"FX6_VSR68x appfw=%llx fb=%p\n",(unsigned long long)g_appfw,fb);
    if(!g_appfw||!fb) return;
    fx6_gds_install(fb);
    int (*setcwd)(const char*)=(int(*)(const char*))dlsym((void*)-1,"_ZN2ux4core6Kernel23sys_setCurrentDirectoryEPKc");
    int (*setdb)(const char*)=(int(*)(const char*))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager11setDatabaseEPKc");
    int (*setns)(unsigned short)=(int(*)(unsigned short))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager28sys_setFontNameWithNamespaceEt");
    int (*swbank)(unsigned short,unsigned char)=(int(*)(unsigned short,unsigned char))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager10switchBankEth");
    int (*proccmd)(unsigned int)=(int(*)(unsigned int))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager15processCommandsEj");
    if(setcwd) setcwd("/usr/share/app/");
    if(setdb) dprintf(2,"FX6_VSR68x setdb=%d\n",setdb("global.xdb"));
    if(setns) dprintf(2,"FX6_VSR68x setns=%d\n",setns(5));
    if(swbank){ dprintf(2,"FX6_VSR68x sw0,0=%d\n",swbank(0,0));
                dprintf(2,"FX6_VSR68x sw1,4=%d\n",swbank(1,4));
                dprintf(2,"FX6_VSR68x sw2,4=%d\n",swbank(2,4)); }
    fx6_add_arena(0,0x100000U,0x800000U);
    fx6_add_arena(1,0x080000U,0x400000U);
    fx6_add_arena(2,0x080000U,0x200000U);
    fx6_load_fonts();
    fx6_model_ready(g_appfw);
    fx6_engine_gate_auto();

#if defined(PAGE_PROJECT)
    page_project(g_appfw);
#elif defined(PAGE_CENTER)
    page_center(g_appfw);
#elif defined(PAGE_SETTING)
    page_setting(g_appfw);
#endif
    if (proccmd) proccmd(0);
    dprintf(2,"FX6_VSR68x done text=%d fill=%d icon=%d text_ok=%d\n",
            g_text_n,g_fill_n,g_icon_n,g_text_ok);
    fx6_scan_osd();
}
