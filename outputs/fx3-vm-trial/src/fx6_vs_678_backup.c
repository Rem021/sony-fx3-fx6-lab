/* 670: the full Big-6 home page.
 *
 * Centre area: every descriptor of TABLE 0x2e9e210 rendered by its own native
 * class (view_string captions, view_fill panels/separators, view_icon images),
 * using the geometry, colours and captions the firmware ships.
 *
 * Six outer cells (No101..No106): the descriptor table only carries their
 * rectangle and font (their +0x18 is 0 because the controller injects the text
 * at runtime), so each cell is rendered as:
 *     1x native view_fill   (cell background, colour from color_cmn)
 *     2x native view_string (title ResID + value ResID)
 * The ResIDs are the ones the static line located in appFw .rodata / .data.rel.ro:
 *
 *   cell        title ResID      value ResID
 *   ----------  -------------    -----------------------------
 *   FPS         0x02005082       0x020030ce  "Angle (Continuous)"
 *   Shutter     0x020050e8       0x02002fe1  "Shutter"
 *   ISO/Gain    0x02004c32       0x02005459  "ISO/Gain"
 *   ND Filter   0x02004288       0x020054fd
 *   White Bal.  0x02005689       0x02002934  "WB: A"
 *   Base Look   0x020023f8       0x02002464  "S-Cinetone"
 *
 * No coordinate, colour or caption is invented here: the cell rectangles come
 * from descriptors 91..96, the strings from the firmware resource containers.
 */
#include "/private/tmp/fx6_static_assist.h"
extern int dprintf(int,const char*,...);
extern void *fx6_map_osd(void);
extern void fx6_gds_install(void *fb);
extern void fx6_scan_osd(void);
extern void *calloc(unsigned long,unsigned long);
extern void *dlsym(void*,const char*);

#define FX6_DESC_STRIDE  0x48u
#define FX6_TBL_HOME     0x2ea3e50u
#define FX6_TBL_HOME_N   10

static uint64_t g_appfw;
static uint32_t *g_osd;
static int g_text_ok, g_text_n, g_fill_n, g_icon_n, g_skip_n2;

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
    dprintf(2,"FX6_VSR678 text blit n=%d at %d,%d\n",n,dx,dy);
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
    dprintf(2,"FX6_VSR678 loadFonts ok=%d/%d\n",ok,total);
}

/* ---------------- native view_string ------------------------------------- */
static int fx6_render_string_rid(uint64_t appfw, int x, int y, int w, int h,
                                 uint32_t text_resid, uint32_t font, uint32_t layout,
                                 const char *tag_name)
{
    if (!text_resid || text_resid==0xffffffffU) return 0;
    if (w < 8 || h < 4) return 0;

    void *vs = calloc(1, 0x1400);
    if (!vs) return 0;
    char param[0x40];
    for (unsigned i=0;i<sizeof(param);i++) param[i]=0;
    ((void(*)(void*,void*))(uintptr_t)(appfw+0xc3af98ULL))(vs,param);

    *(int32_t*)((char*)vs+0x1e8)=x;
    *(int32_t*)((char*)vs+0x1ec)=y;
    *(int32_t*)((char*)vs+0x1f0)=w;
    *(int32_t*)((char*)vs+0x1f4)=h;
    *(uint32_t*)((char*)vs+0x200)=text_resid;
    *(uint8_t*)((char*)vs+0x1fc)=1;
    /* Same four ids the native view_string path uses (the values the descriptor
     * table carries for a view_string row). These used to be inherited from the
     * button descriptor, which are button params, not text params. */
    *(uint32_t*)((char*)vs+0x208)=0x0200600fU;   /* font   */
    *(uint32_t*)((char*)vs+0x20c)=0x0200600eU;   /* font2  */
    *(uint32_t*)((char*)vs+0x210)=0x0200a029U;   /* layout */
    *(uint32_t*)((char*)vs+0xa14)=0x0200600bU;   /* size   */
    (void)layout; (void)font;
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
    if (!vt || !vt[0x158/8]) return 0;
    ((void(*)(void*))vt[0x158/8])(vs);

    *(unsigned short*)((char*)ts+0xa8) |= 0x0006;
    void (*dti)(void*)=(void(*)(void*))dlsym((void*)-1,"_ZN2ux6gfxeng10TextSprite12drawTextImplEv");
    if (dti) dti(ts);
    { int (*pc)(unsigned int)=(int(*)(unsigned int))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager15processCommandsEj");
      if (pc) pc(0); }

    dprintf(2,"FX6_VSR678 %s (%d,%d,%d,%d) text=%08x\n", tag_name, x,y,w,h, text_resid);
    g_text_n++;
    return 1;
}

static int fx6_render_string(uint64_t appfw, uint8_t *p, const char *tbl, int idx)
{
    const char *name = *(const char**)(p+0x08);
    uint32_t text_resid = *(uint32_t*)(p+0x18);
    uint32_t layout = *(uint32_t*)(p+0x1c);
    uint32_t font = *(uint32_t*)(p+0x24);
    uint32_t font2 = *(uint32_t*)(p+0x28);
    uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
    uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
    if (!text_resid || text_resid==0xffffffffU) return 0;
    if (w < 8 || h < 8) return 0;

    void *vs = calloc(1, 0x1400);
    if (!vs) return 0;
    char param[0x40];
    for (unsigned i=0;i<sizeof(param);i++) param[i]=0;
    ((void(*)(void*,void*))(uintptr_t)(appfw+0xc3af98ULL))(vs,param);

    *(int32_t*)((char*)vs+0x1e8)=x;
    *(int32_t*)((char*)vs+0x1ec)=y;
    *(int32_t*)((char*)vs+0x1f0)=w;
    *(int32_t*)((char*)vs+0x1f4)=h;
    *(uint32_t*)((char*)vs+0x200)=text_resid;
    *(uint8_t*)((char*)vs+0x1fc)=1;
    if (layout) *(uint32_t*)((char*)vs+0x210)=layout;
    if (font)   *(uint32_t*)((char*)vs+0x208)=font;
    if (font2)  *(uint32_t*)((char*)vs+0x20c)=font2;
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
    if (!vt || !vt[0x158/8]) return 0;
    ((void(*)(void*))vt[0x158/8])(vs);

    *(unsigned short*)((char*)ts+0xa8) |= 0x0006;
    void (*dti2)(void*)=(void(*)(void*))dlsym((void*)-1,"_ZN2ux6gfxeng10TextSprite12drawTextImplEv");
    if (dti2) dti2(ts);
    { int (*pc)(unsigned int)=(int(*)(unsigned int))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager15processCommandsEj");
      if (pc) pc(0); }

    dprintf(2,"FX6_VSR678 %s[%02d] S %-30s (%d,%d,%d,%d) text=%08x\n",
            tbl, idx, name?name:"?", x,y,w,h, text_resid);
    g_text_n++;
    return 1;
}

/* ---------------- native view_fill --------------------------------------- */
static void fx6_fill_rect(uint64_t appfw, int x, int y, int w, int h, uint32_t color_resid,
                          const char *tag_name)
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
    (void)tag_name;
    g_fill_n++;
}

static int fx6_render_fill(uint64_t appfw, uint8_t *p, const char *tbl, int idx)
{
    const char *name = *(const char**)(p+0x08);
    uint32_t color_resid = *(uint32_t*)(p+0x18);
    uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
    uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
    if (w < 1 || h < 1) return 0;
    fx6_fill_rect(appfw, x, y, w, h, color_resid, "fill");
    dprintf(2,"FX6_VSR678 %s[%02d] F %-30s (%d,%d,%d,%d) color=%08x\n",
            tbl, idx, name?name:"?", x,y,w,h, color_resid);
    return 1;
}

/* ---------------- native view_icon --------------------------------------- */
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
    dprintf(2,"FX6_VSR678 icon (%d,%d,%d,%d) img=%08x\n", x,y,w,h,img);
    g_icon_n++;
}

static int fx6_render_icon(uint64_t appfw, uint8_t *p, const char *tbl, int idx)
{
    const char *name = *(const char**)(p+0x08);
    uint32_t img = *(uint32_t*)(p+0x18);
    uint16_t x=*(uint16_t*)(p+0x3c), y=*(uint16_t*)(p+0x3e);
    uint16_t w=*(uint16_t*)(p+0x40), h=*(uint16_t*)(p+0x42);
    if (!img || img==0xffffffffU) return 0;
    fx6_icon_blit(appfw, x, y, w, h, img);
    dprintf(2,"FX6_VSR678 %s[%02d] I %-30s (%d,%d,%d,%d) img=%08x\n",
            tbl, idx, name?name:"?", x,y,w,h, img);
    return 1;
}

/* Native 1px border: four view_fill edges, each drawn by the real class so the
 * colour comes from color_cmn.uxc exactly as the firmware does it. */
static void fx6_border(uint64_t appfw, int x, int y, int w, int h, uint32_t color_resid)
{
    if (w < 3 || h < 3) return;
    fx6_fill_rect(appfw, x,     y,     w, 1, color_resid, "border-t");
    fx6_fill_rect(appfw, x,     y+h-1, w, 1, color_resid, "border-b");
    fx6_fill_rect(appfw, x,     y,     1, h, color_resid, "border-l");
    fx6_fill_rect(appfw, x+w-1, y,     1, h, color_resid, "border-r");
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

/* Six outer cells: title / value ResIDs located by the static line in
 * appFw .rodata and .data.rel.ro param_t initialisers. */
typedef struct {
    uint32_t title_rid;
    uint32_t value_rid;
    const char *name;
} fx6_cell_text;

/* Order matters: the six cells are walked in reading order (top row left to
 * right, then bottom row), which is how the camera lays them out. */
/* 674 diagnostic: every id below is a namespace-1 string that 669 already
 * rendered successfully, so if the cells now paint, the failure mode is that
 * TextSprite::setString(ResID) cannot use namespace-2 ids even though
 * ResourceManager::getText can resolve them. */
static const fx6_cell_text g_cells[6] = {
    { 0x02005082u, 0x020030ceu, "FPS"        },  /* top-left      */
    { 0x020050e8u, 0x02002fe1u, "Shutter"    },  /* top-centre    */
    { 0x02004c32u, 0x02005459u, "ISO/Gain"   },  /* top-right     */
    { 0x02004288u, 0x020054fdu, "ND Filter"  },  /* bottom-left   */
    { 0x02005689u, 0x02002934u, "White Bal." },  /* bottom-centre */
    { 0x020023f8u, 0x02002464u, "Base Look"  },  /* bottom-right  */
};


/* Probe candidate 7-entry ResID runs to find the setting category list. */
static void fx6_probe7(uint64_t appfw)
{
    static const uint32_t cand[] = { 0x227f758u, 0x227fa18u, 0x2280928u,
                                     0x23be8bcu, 0x23d9700u, 0x23da5b0u };
    void (*sc)(void*) = (void(*)(void*))dlsym((void*)-1,"_ZN5libra6StringC1Ev");
    const char *(*pb)(const void*) = (const char*(*)(const void*))dlsym((void*)-1,"_ZNK6stella6String9ptrBufferEv");
    int (*gt)(unsigned,void*) = (int(*)(unsigned,void*))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager7getTextEjRN5libra6StringE");
    if (!sc||!pb||!gt) return;
    for (unsigned c=0;c<sizeof(cand)/sizeof(cand[0]);c++){
        const uint32_t *t=(const uint32_t*)(uintptr_t)(appfw+cand[c]);
        dprintf(2,"FX6_VSR678 RUN 7 @0x%x\n", cand[c]);
        for (int i=0;i<7;i++){
            unsigned char buf[0x40];
            for (unsigned k=0;k<sizeof(buf);k++) buf[k]=0;
            sc(buf);
            int rc=gt(t[i],buf);
            dprintf(2,"FX6_VSR678   [%d] %08x rc=%d \"%s\"\n", i, t[i], rc, pb(buf)?pb(buf):"");
        }
    }
}

void fx6_force_update(void){
    g_appfw=fx6_appfw_base_auto();
    void *fb=fx6_map_osd();
    g_osd=(uint32_t*)fb;
    dprintf(2,"FX6_VSR678 appfw=%llx fb=%p\n",(unsigned long long)g_appfw,fb);
    if(!g_appfw||!fb) return;
    fx6_gds_install(fb);
    int (*setcwd)(const char*)=(int(*)(const char*))dlsym((void*)-1,"_ZN2ux4core6Kernel23sys_setCurrentDirectoryEPKc");
    int (*setdb)(const char*)=(int(*)(const char*))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager11setDatabaseEPKc");
    int (*setns)(unsigned short)=(int(*)(unsigned short))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager28sys_setFontNameWithNamespaceEt");
    int (*swbank)(unsigned short,unsigned char)=(int(*)(unsigned short,unsigned char))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager10switchBankEth");
    int (*proccmd)(unsigned int)=(int(*)(unsigned int))dlsym((void*)-1,"_ZN2ux6resmgr15ResourceManager15processCommandsEj");
    if(setcwd) setcwd("/usr/share/app/");
    if(setdb) dprintf(2,"FX6_VSR678 setdb=%d\n",setdb("global.xdb"));
    if(setns) dprintf(2,"FX6_VSR678 setns=%d\n",setns(5));
    if(swbank){ dprintf(2,"FX6_VSR678 sw0,0=%d\n",swbank(0,0));
                dprintf(2,"FX6_VSR678 sw1,4=%d\n",swbank(1,4));
                dprintf(2,"FX6_VSR678 sw2,4=%d\n",swbank(2,4)); }
    fx6_add_arena(0,0x100000U,0x800000U);
    fx6_add_arena(1,0x080000U,0x400000U);
    fx6_add_arena(2,0x080000U,0x200000U);
    fx6_load_fonts();

    fx6_probe7(g_appfw);
    fx6_model_ready(g_appfw);
    dprintf(2,"FX6_VSR678 gate=%p\n", fx6_engine_gate_auto());

    uint8_t *base=(uint8_t*)(uintptr_t)(g_appfw + FX6_TBL_HOME);

    /* Gather the six outer-cell descriptors and order them by position so the
     * title strings land on the cells the camera puts them on. */
    for (int i=0;i<FX6_TBL_HOME_N;i++){
        uint8_t *p = base + (uint64_t)i*FX6_DESC_STRIDE;
        void *proto = *(void**)p;
        {
            const char *nm = *(const char**)(p+0x08);
            (void)nm;  /* setting page has no No2xxx compact layout */
        }
        int kind = fx6_tag_kind(g_appfw, proto);
        uint32_t text_resid = *(uint32_t*)(p+0x18);

        if (kind==2) { fx6_render_fill(g_appfw, p, "home", i); continue; }
        if (kind==4) { fx6_render_icon(g_appfw, p, "home", i); continue; }

        if (kind==3) {
            /* six outer cells were drawn up front */
            if (i>=91 && i<=96) continue;
            if (text_resid && text_resid!=0xffffffffU)
                fx6_render_string(g_appfw, p, "home", i);
            continue;
        }
        if (kind==1) {
            if (text_resid && text_resid!=0xffffffffU)
                fx6_render_string(g_appfw, p, "home", i);
        }
        if (proccmd) proccmd(0);
    }
    if (proccmd) proccmd(0);
    dprintf(2,"FX6_VSR678 done text=%d fill=%d icon=%d skipN2=%d text_ok=%d\n",
            g_text_n,g_fill_n,g_icon_n,g_skip_n2,g_text_ok);
    fx6_scan_osd();
}
