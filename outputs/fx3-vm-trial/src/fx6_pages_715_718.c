/* 715–718 — Paint/Keyboard Overlay (102 rows), Media Status (48 rows),
 * Clip Thumbnail Browser 4x3 Grid (39 rows), and Status Icon / Date Picker / HUD Tracking.
 *
 * All four pages render with per-row style + fx6_row_extras enabled (g_use_extras=1)
 * and MI/thumbnail/gauge/9-patch support in page_table().
 *
 *   -DPAGE_A (715): Page 4  (0x02e92c18, 102 rows — Paint / On-Screen Keyboard Text Input Overlay)
 *   -DPAGE_B (716): Page 58 (0x02eaad68,  48 rows — Media Status SSA/SSB/SSP)
 *   -DPAGE_C (717): Page 12 (0x02e9b798,  39 rows — Clip Thumbnail Browser 4x3 Grid)
 *   -DPAGE_D (718): Page 92 (0x02eb44b8,  19 rows — Status Icon / Radio Button Page)
 *                 + Page 28 (0x02ea2e48,  16 rows — Date/Time Touch Picker)
 */
#include "fx6_static_assist.h"
extern int dprintf(int,const char*,...);
extern void *fx6_map_osd(void);
extern void fx6_gds_install(void *fb);
extern void fx6_scan_osd(void);
extern void *calloc(unsigned long,unsigned long);
extern void *dlsym(void*,const char*);
extern void *dlopen(const char*,int);

#define FX6_DESC_STRIDE 0x48u
#define FX6_COLOR_SEL   0x0200c014u
#define VS_ROW_BASE     0x220u
#define VS_ROW_STRIDE   0x5cu
#define VS_ROW_TYPE     (-4)
#define VS_ROW_VALUE    0x54u
#define VS_ROW_COUNT    0x610u
#define VS_TYPE_VALUE   2u

static uint64_t g_appfw;
static uint32_t *g_osd;
static int g_text_ok, g_text_n, g_fill_n, g_icon_n;
static int g_use_extras = 1;

void fx6_model_done(void){ dprintf(2,"FX6_MODEL_NONE\n"); }

void _ZN5libra10Dictionary6addRowERKNS_6StringERKNS_7VariantE(void *self, const void *k, const void *v) {
    if (!self) return;
    typedef void (*fn_t)(void *, const void *, const void *);
    static fn_t real;
    if (!real) {
        void *h = dlopen("/usr/lib/liblibra.so", 1);
        if (h) real = (fn_t)dlsym(h, "_ZN5libra10Dictionary6addRowERKNS_6StringERKNS_7VariantE");
    }
    if (real) real(self, k, v);
}

static int strcmp_(const char *a, const char *b) {
    if (!a||!b) return 1;
    while (*a && *b && *a==*b) { a++; b++; }
    return (int)(unsigned char)*a - (int)(unsigned char)*b;
}

static int fx6_blit_imagedata_to_osd(void *image, uint32_t *osd, int dst_x, int dst_y) {
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

static void fx6_text_image_cb(void *ts, void *image, void *ud) {
    (void)ts;
    int dx = 0, dy = 0;
    if (ud) { dx = *(int32_t*)((char*)ud+0x1e8); dy = *(int32_t*)((char*)ud+0x1ec); }
    int n = fx6_blit_imagedata_to_osd(image, g_osd, dx, dy);
    if (n) g_text_ok++;
}

static int fx6_add_arena(int idx, unsigned min, unsigned max) {
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

static void fx6_load_fonts(void) {
    int (*ld)(unsigned int)=(int(*)(unsigned int))
        dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager16sys_loadFontDataEj");
    if (!ld) return;
    int ok=0,total=0;
    for (unsigned r=0x02006000U; r<=0x0200603fU; r++){ total++; if (ld(r)) ok++; }
    for (unsigned r=0x0200a000U; r<=0x0200a02fU; r++){ total++; if (ld(r)) ok++; }
    for (unsigned r=0x02008000U; r<=0x0200800fU; r++){ total++; if (ld(r)) ok++; }
    dprintf(2,"FX6_VSR71x loadFonts ok=%d/%d\n",ok,total);
}

static int fx6_text_of(uint32_t rid, char *out, unsigned outsz) {
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

static void fx6_fill_rect(uint64_t appfw, int x, int y, int w, int h, uint32_t color_resid) {
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

static void fx6_icon_blit(uint64_t appfw, int x, int y, int w, int h, uint32_t img) {
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

typedef struct {
    const char *widget;
    unsigned char mode;
    unsigned int primary;
    unsigned int v1;
    unsigned int v2;
} hud_bind_t;

static const hud_bind_t g_hud[] = {
    {"No31_clip_name",0,0x020050c4u,0,0},
    {"No32_video_codec",0,0x02002f1eu,0,0},
    {"No33_video_size",0,0x02002999u,0,0},
    {"No34_video_fps",0,0x0200532du,0,0},
    {"No35_rec_mode",0,0x020050a7u,0,0},
    {"No8_content_num",0,0x02002385u,0,0},
    {"No1023_gain_value",1,0x020020fcu,800,0},
    {"No1022_sandq_frame_rate_value",1,0x020020a6u,24,0},
};
#define HUD_N ((int)(sizeof(g_hud)/sizeof(g_hud[0])))

static const hud_bind_t *fx6_hud_for(const char *name) {
    if (!name) return 0;
    for (int i=0;i<HUD_N;i++) if (!strcmp_(g_hud[i].widget, name)) return &g_hud[i];
    return 0;
}

static void fx6_vs_set_vn(void *vs, unsigned idx, unsigned val) {
    if (!*(void **)((char *)vs + 0x1030)) {
        void *dict = calloc(1, 0x80);
        void (*dc)(void *) = (void (*)(void *))dlsym((void *)-1, "_ZN5libra10DictionaryC1Ev");
        if (dict && dc) { dc(dict); *(void **)((char *)vs + 0x1030) = dict; }
    }
    char *row=(char*)vs + VS_ROW_BASE + (unsigned long)idx*VS_ROW_STRIDE;
    *(int*)(row+VS_ROW_TYPE)=(int)VS_TYPE_VALUE;
    *(unsigned*)(row+VS_ROW_VALUE)=val;
    unsigned cnt=*(unsigned*)((char*)vs+VS_ROW_COUNT);
    if (cnt<=idx) *(unsigned*)((char*)vs+VS_ROW_COUNT)=idx+1u;
}

static void fx6_render_row(uint64_t appfw, uint8_t *p, const char *tag) {
    const char *name = *(const char**)(p+0x08);
    uint32_t d18 = *(uint32_t*)(p+0x18);
    uint32_t layout = *(uint32_t*)(p+0x1c);
    uint32_t font = *(uint32_t*)(p+0x24);
    uint32_t font2 = *(uint32_t*)(p+0x28);
    uint32_t d30 = *(uint32_t*)(p+0x30);
    uint32_t d34 = *(uint32_t*)(p+0x34);
    uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
    uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
    if (w < 8 || h < 4) return;

    const hud_bind_t *b = fx6_hud_for(name);
    if (!b && (!d18 || d18==0xffffffffU)) return;
    if (!b) {
        char probe[0x60];
        if (!fx6_text_of(d18, probe, sizeof(probe))) return;
    }

    void *vs = calloc(1, 0x1400);
    if (!vs) return;
    char param[0x40];
    for (unsigned i=0;i<sizeof(param);i++) param[i]=0;
    ((void(*)(void*,void*))(uintptr_t)(appfw+0xc3af98ULL))(vs,param);

    *(int32_t*)((char*)vs+0x1e8)=x;
    *(int32_t*)((char*)vs+0x1ec)=y;
    *(int32_t*)((char*)vs+0x1f0)=w;
    *(int32_t*)((char*)vs+0x1f4)=h;
    *(uint32_t*)((char*)vs+0x208)=(g_use_extras && font) ? font : 0x0200600fU;
    *(uint32_t*)((char*)vs+0x20c)=(g_use_extras && font2) ? font2 : 0x0200600eU;
    *(uint32_t*)((char*)vs+0x210)=(g_use_extras && layout) ? layout : 0x0200a029U;
    *(uint32_t*)((char*)vs+0xa14)=0x0200600bU;
    *(int*)((char*)vs+0x214)=0;
    if (g_use_extras && d30) *(uint32_t*)((char*)vs+0x218)=d30;
    *(uint32_t*)((char*)vs+0x21c)=(g_use_extras && d34) ? d34 : 1U;
    *(uint32_t*)((char*)vs+0xa30)=0x0200a005U;

    if (b) {
        if (b->mode == 0) {
            *(uint32_t*)((char*)vs+0x200)=b->primary;
        } else {
            if (b->primary) *(uint32_t*)((char*)vs+0x200)=b->primary;
            fx6_vs_set_vn(vs,0,b->v1);
            if (b->mode==2) fx6_vs_set_vn(vs,1,b->v2);
        }
    } else {
        *(uint32_t*)((char*)vs+0x200)=d18;
    }
    *(uint8_t*)((char*)vs+0x1fc)=1;
    *(int*)((char*)vs+0x610)= (b && b->mode) ? (b->mode==2?2:1) : *(int*)((char*)vs+0x610);

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
    (void)tag;
    g_text_n++;
}

static void page_table(uint64_t appfw, uint32_t off, int count, const char *label) {
    uint8_t *base = (uint8_t *)(uintptr_t)(appfw + off);
    int thumb_idx = 0;
    for (int i = 0; i < count; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void **)p - appfw);
        uint32_t c = *(uint32_t *)(p + 0x18);
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        if (tag == 0x42d5a40u || tag == 0x42d57d0u) {
            if (c && c != 0xffffffffU)
                fx6_fill_rect(appfw, x, y, w, h, c);
        } else if (tag == 0x42d5a50u && w >= 140 && h >= 48) {
            if (c && c != 0xffffffffU)
                fx6_icon_blit(appfw, x, y, w, h, c);
        } else if (tag == 0x42d58d0u && w >= 36 && h >= 36 && w < 900) {
            fx6_fill_rect(appfw, x, y, w, h, 0x0200c008u);
        } else if (tag == 0x42d58f0u && w >= 60 && h >= 40) {
            if (thumb_idx == 11) {
                fx6_fill_rect(appfw, x - 2, y - 2, w + 4, h + 4, FX6_COLOR_SEL);
            }
            fx6_fill_rect(appfw, x, y, w, h, 0x0200c008u);
            thumb_idx++;
        } else if (tag == 0x42d58b0u && w >= 40 && h >= 6) {
            fx6_fill_rect(appfw, x, y, w, h, 0x0200c008u);
            fx6_fill_rect(appfw, x, y, (w * 2) / 3, h, 0x0200c013u);
        }
    }
    for (int i = 0; i < count; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void **)p - appfw);
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        if (tag == 0x42d57f0u || tag == 0x42d59a0u || tag == 0x42d58d0u) {
            fx6_render_row(appfw, p, label);
        } else if (tag == 0x42d5a50u && !(w >= 140 && h >= 48)) {
            uint32_t c = *(uint32_t *)(p + 0x18);
            if (c && c != 0xffffffffU)
                fx6_icon_blit(appfw, x, y, w, h, c);
        }
    }
}

void fx6_force_update(void) {
    g_appfw=fx6_appfw_base_auto();
    void *fb=fx6_map_osd();
    g_osd=(uint32_t*)fb;
    dprintf(2,"FX6_VSR71x appfw=%llx fb=%p\n",(unsigned long long)g_appfw,fb);
    if(!g_appfw||!fb) return;
    fx6_gds_install(fb);
    int (*setcwd)(const char*)=(int(*)(const char*))dlsym((void*)-1,"_ZN2ux4core6Kernel23sys_setCurrentDirectoryEPKc");
    int (*setdb)(const char*)=(int(*)(const char*))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager11setDatabaseEPKc");
    int (*setns)(unsigned short)=(int(*)(unsigned short))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager28sys_setFontNameWithNamespaceEt");
    int (*swbank)(unsigned short,unsigned char)=(int(*)(unsigned short,unsigned char))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager10switchBankEth");
    int (*proccmd)(unsigned int)=(int(*)(unsigned int))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager15processCommandsEj");
    if(setcwd) setcwd("/usr/share/app/");
    if(setdb) dprintf(2,"FX6_VSR71x setdb=%d\n",setdb("global.xdb"));
    if(setns) dprintf(2,"FX6_VSR71x setns=%d\n",setns(5));
    if(swbank){ swbank(0,0); swbank(1,4); swbank(2,4); }
    fx6_add_arena(0,0x100000U,0x800000U);
    fx6_add_arena(1,0x080000U,0x400000U);
    fx6_add_arena(2,0x080000U,0x200000U);
    fx6_load_fonts();
    fx6_model_ready(g_appfw);
    fx6_engine_gate_auto();

#if defined(PAGE_A)
    page_table(g_appfw, 0x2e92c18u, 102, "paintoverlay102");
#elif defined(PAGE_B)
    page_table(g_appfw, 0x2eaad68u, 48, "mediastatus48");
#elif defined(PAGE_C)
    page_table(g_appfw, 0x2e9b798u, 39, "clipgrid39");
#elif defined(PAGE_D)
    page_table(g_appfw, 0x2eb44b8u, 19, "statusicon19");
#endif
    if (proccmd) proccmd(0);
    dprintf(2,"FX6_VSR71x done text=%d fill=%d icon=%d text_ok=%d extras=%d\n",
            g_text_n,g_fill_n,g_icon_n,g_text_ok,g_use_extras);
    fx6_scan_osd();
}
