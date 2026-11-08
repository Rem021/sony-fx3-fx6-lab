/* 659: make appFw paint panels, separators and a frame — the "border/list-item" half of the goal.
 *
 * Run 658 proved text works (4 captions, text_ok=4) but reported fill=0 icon=0. The cause is the
 * view_fill gate at appFw+0xc2750c:
 *
 *     if (+0x1fc == 0)                      -> mode 3, nothing drawn
 *     if (+0x200 == -1 && +0x208 == 0)      -> mode 3, nothing drawn
 *     else if (+0x200 != -1)                  Sprite::setRectColorResID(slot, +0x200)   [0xc275ec]
 *     else                                    inline colour from +0x205..+0x208          [0xc27684]
 *
 * So a fill needs an enabled flag plus a colour, either as a namespace-6 ResID or as 4 inline bytes.
 *
 * This probe draws, using native constructors only:
 *   A  view_fill 0xc27698  solid panel       (inline colour path)
 *   B  view_fill 0xc27698  colour ResID      (resource path, ids measured in color_cmn.uxc)
 *   C  view_fill 0xc27698  2px separator     (the No10_SEPARATOR shape: w=820 h=2)
 *   D  view_frame 0xc27800 border            (ctor builds 5 nested view_fill children itself)
 *   E  view_string 0xc3af98 caption          (control: text still renders)
 *
 * Acceptance: non-zero pixels inside each rect, with the fill rects yielding a *block* of one
 * colour (not a single row), and the frame yielding four edges rather than a solid block.
 */
#include "/private/tmp/fx6_static_assist.h"
extern int dprintf(int, const char *, ...);
extern void *fx6_map_osd(void);
extern void fx6_gds_install(void *fb);
extern void fx6_scan_osd(void);
extern void *calloc(unsigned long, unsigned long);
extern void *dlsym(void *, const char *);

static uint64_t g_appfw;
static uint32_t *g_osd;

/* colour ids verified in color_cmn.uxc (namespace 6, marker 0x3a00, payload u32 RGBA) */
#define COL_BLACK   0x0200c001u   /* 000000ff */
#define COL_SEP     0x0200c00eu   /* 777777ff */
#define COL_WHITE   0x0200c019u   /* ffffffff */
#define COL_ACCENT  0x0200c011u   /* ee0000ff */

static uint64_t fx6_mod_base(const char *sym)
{
    if (!sym) return 0;
    void *s = dlsym((void *)-1, sym);
    if (!s) return 0;
    fx6_dl_info di;
    for (unsigned i = 0; i < sizeof(di); i++) ((char *)&di)[i] = 0;
    if (!dladdr(s, &di) || !di.dli_fbase) return 0;
    return (uint64_t)(uintptr_t)di.dli_fbase;
}

static int fx6_add_arena(int idx, unsigned min, unsigned max)
{
    unsigned char param[0x20];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    void *buf = calloc(1, max);
    if (!buf) return 0;
    *(unsigned *)(param + 0x00) = max;
    *(unsigned *)(param + 0x04) = min;
    *(unsigned *)(param + 0x08) = max;
    *(void **)(param + 0x10) = buf;
    *(unsigned char *)(param + 0x19) = 1;
    *(unsigned char *)(param + 0x1a) = 0xff;
    *(unsigned char *)(param + 0x1b) = 3;
    int (*add)(unsigned char, const void *) = (int (*)(unsigned char, const void *))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager8addArenaEhRKN5libra10ArenaParamE");
    return add ? add((unsigned char)idx, (const void *)param) : 0;
}

static void fx6_load_fonts(void)
{
    int (*ld)(unsigned int) = (int (*)(unsigned int))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager16sys_loadFontDataEj");
    if (!ld) return;
    int ok = 0, total = 0;
    for (unsigned r = 0x02006000U; r <= 0x0200603fU; r++) { total++; if (ld(r)) ok++; }
    for (unsigned r = 0x0200a000U; r <= 0x0200a02fU; r++) { total++; if (ld(r)) ok++; }
    for (unsigned r = 0x02008000U; r <= 0x0200800fU; r++) { total++; if (ld(r)) ok++; }
    dprintf(2, "FX6_FILL659 loadFonts ok=%d/%d\n", ok, total);
}

/* Count non-zero pixels and how many distinct rows carry content. A solid panel gives many rows;
 * a failed fill gives none; a stray single-pixel row is not accepted as a panel. */
static int fx6_scan_rect(int x0, int y0, int w, int h, const char *tag)
{
    int n = 0, rows = 0, cols = 0, fx = -1, fy = -1, lx = -1, ly = -1;
    if (!g_osd) return 0;
    for (int y = y0; y < y0 + h && y < 540; y++) {
        if (y < 0) continue;
        for (int x = x0; x < x0 + w && x < 1024; x++) {
            if (x < 0) continue;
            if (g_osd[y * 1024 + x]) {
                n++;
                if (fx < 0 || x < fx) fx = x;
                if (fy < 0 || y < fy) fy = y;
                if (x > lx) lx = x;
                if (y > ly) ly = y;
            }
        }
        int has = 0;
        for (int x = x0; x < x0 + w && x < 1024; x++)
            if (x >= 0 && g_osd[y * 1024 + x]) { has = 1; break; }
        if (has) rows++;
    }
    for (int x = x0; x < x0 + w && x < 1024; x++) {
        if (x < 0) continue;
        for (int y = y0; y < y0 + h && y < 540; y++)
            if (y >= 0 && g_osd[y * 1024 + x]) { cols++; break; }
    }
    dprintf(2, "FX6_FILL659 %s nonzero=%d rows=%d cols=%d bbox=(%d,%d)-(%d,%d)\n",
            tag, n, rows, cols, fx, fy, lx, ly);
    return n;
}

/* ---- native view_fill: ctor 0xc27698, onDraw 0xc2750c ---- */
static void *fx6_make_fill(uint64_t appfw, int x, int y, int w, int h)
{
    void *p = calloc(1, 0x400);
    if (!p) return 0;
    char param[0x40];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc27698ULL))(p, param);
    *(int *)((char *)p + 0x1e8) = x;
    *(int *)((char *)p + 0x1ec) = y;
    *(int *)((char *)p + 0x1f0) = w;
    *(int *)((char *)p + 0x1f4) = h;
    return p;
}

static void fx6_fill_draw(uint64_t appfw, void *p, const char *tag)
{
    if (!p) { dprintf(2, "FX6_FILL659 %s null\n", tag); return; }
    void **vt = *(void ***)p;
    if (!vt) return;
    /* hardware path: the widget's own onCreate then onDrawNotice */
    if (vt[0x148 / 8]) ((void (*)(void *))vt[0x148 / 8])(p);
    if (vt[0x158 / 8]) ((void (*)(void *))vt[0x158 / 8])(p);
    else dprintf(2, "FX6_FILL659 %s no onDraw\n", tag);
}

/* ---- native view_frame: ctor 0xc27800, onDraw 0xc27ea0 ---- */
static void *fx6_make_frame(uint64_t appfw, int x, int y, int w, int h)
{
    void *p = calloc(1, 0x1400);
    if (!p) return 0;
    char param[0x40];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc27800ULL))(p, param);
    *(int *)((char *)p + 0x1e8) = x;
    *(int *)((char *)p + 0x1ec) = y;
    *(int *)((char *)p + 0x1f0) = w;
    *(int *)((char *)p + 0x1f4) = h;
    return p;
}

static void fx6_draw_text(uint64_t appfw, int x, int y, int w, int h, uint32_t resid)
{
    void *p = calloc(1, 0x1400);
    if (!p) return;
    char param[0x40];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc3af98ULL))(p, param);
    *(int *)((char *)p + 0x1e8) = x;
    *(int *)((char *)p + 0x1ec) = y;
    *(int *)((char *)p + 0x1f0) = w;
    *(int *)((char *)p + 0x1f4) = h;
    *(unsigned char *)((char *)p + 0x1fc) = 1;
    *(unsigned int  *)((char *)p + 0x200) = resid;
    *(unsigned int  *)((char *)p + 0xa30) = 0x0200a005u;
    *(unsigned int  *)((char *)p + 0x208) = 0x02006001u;
    *(unsigned int  *)((char *)p + 0x20c) = 0x02008000u;
    *(unsigned int  *)((char *)p + 0x210) = 0x0200a029u;
    *(int *)((char *)p + 0x610) = 0;
    void **vt = *(void ***)p;
    if (vt && vt[0x158 / 8]) ((void (*)(void *))vt[0x158 / 8])(p);
}

void fx6_model_done(void) { dprintf(2, "FX6_MODEL_NONE\n"); }

void fx6_force_update(void)
{
    g_appfw = fx6_mod_base("_ZN2ux6resmgr15ResourceManager11setDatabaseEPKc");
    void *fb = fx6_map_osd();
    dprintf(2, "FX6_FILL659 appfw=%llx fb=%p\n", (unsigned long long)g_appfw, fb);
    g_osd = (uint32_t *)fb;
    if (!g_appfw || !fb) return;

    fx6_gds_install(fb);

    int (*setcwd)(const char *) = (int (*)(const char *))
        dlsym((void *)-1, "_ZN2ux4core6Kernel23sys_setCurrentDirectoryEPKc");
    int (*setdb)(const char *) = (int (*)(const char *))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager11setDatabaseEPKc");
    int (*setns)(unsigned short) = (int (*)(unsigned short))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager28sys_setFontNameWithNamespaceEt");
    if (setcwd) setcwd("/usr/share/app/");
    if (setdb) dprintf(2, "FX6_FILL659 setdb=%d\n", setdb("global.xdb"));
    if (setns) dprintf(2, "FX6_FILL659 setns=%d\n", setns(5));

    fx6_add_arena(0, 0x100000U, 0x800000U);
    fx6_add_arena(1, 0x080000U, 0x400000U);
    fx6_add_arena(2, 0x080000U, 0x200000U);
    fx6_load_fonts();

    /* A: inline colour path — proves the 0xc27684 branch paints a block */
    void *a = fx6_make_fill(g_appfw, 60, 60, 400, 120);
    if (a) {
        *(unsigned char  *)((char *)a + 0x1fc) = 1;
        *(unsigned int   *)((char *)a + 0x200) = 0xffffffffu;   /* no ResID -> inline path */
        *(unsigned char  *)((char *)a + 0x205) = 0x22;
        *(unsigned char  *)((char *)a + 0x206) = 0x33;
        *(unsigned char  *)((char *)a + 0x207) = 0x44;
        *(unsigned char  *)((char *)a + 0x208) = 0xff;
        fx6_fill_draw(g_appfw, a, "A_inline");
        fx6_scan_rect(60, 60, 400, 120, "A_inline");
    }

    /* B: resource colour path — proves setRectColorResID resolves a color_cmn id */
    void *b = fx6_make_fill(g_appfw, 500, 60, 400, 120);
    if (b) {
        *(unsigned char *)((char *)b + 0x1fc) = 1;
        *(unsigned int  *)((char *)b + 0x200) = COL_SEP;
        fx6_fill_draw(g_appfw, b, "B_resid");
        fx6_scan_rect(500, 60, 400, 120, "B_resid");
    }

    /* C: the exact separator shape from the tables (No10_SEPARATOR: 820x2 at y=94) */
    void *c = fx6_make_fill(g_appfw, 60, 300, 820, 2);
    if (c) {
        *(unsigned char *)((char *)c + 0x1fc) = 1;
        *(unsigned int  *)((char *)c + 0x200) = 0x0200c00bu;
        fx6_fill_draw(g_appfw, c, "C_sep");
        fx6_scan_rect(60, 300, 820, 2, "C_sep");
    }

    /* D: view_frame — its ctor builds five nested view_fill children */
    void *d = fx6_make_frame(g_appfw, 500, 300, 300, 120);
    if (d) {
        *(unsigned char *)((char *)d + 0x1fc) = 1;
        void **vt = *(void ***)d;
        if (vt && vt[0x158 / 8]) ((void (*)(void *))vt[0x158 / 8])(d);
        fx6_scan_rect(500, 300, 300, 120, "D_frame");
    }

    /* E: caption control */
    fx6_draw_text(g_appfw, 60, 450, 320, 36, 0x02002227u);
    fx6_scan_rect(60, 450, 320, 36, "E_text");

    int (*proccmd)(unsigned int) = (int (*)(unsigned int))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");
    if (proccmd) proccmd(0);

    dprintf(2, "FX6_FILL659 done\n");
    fx6_scan_osd();
}
