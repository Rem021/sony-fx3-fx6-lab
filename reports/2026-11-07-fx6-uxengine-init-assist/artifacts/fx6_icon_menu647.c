/* 647: make appFw paint a real menu icon, using only its own code paths.
 *
 * Everything here comes from fx6_menu_items_assist.h, which records the appFw facts:
 *   view_icon ctor     0xc2c188   (size 0x668, creator index 0)
 *   view_icon onDraw   0xc2d100
 *   the two fields that matter:  +0x1fc = 1 (enabled), +0x20c = image ResID
 *   the ids appFw installs itself at 0xc1f858: 0x02000488 / 0x02000484 / 0x020003c7
 *
 * Two icons are drawn side by side, then one view_string caption, so the same frame contains
 * both an image widget and a text widget. Acceptance is non-zero pixels inside each requested
 * rect, plus the ImageData callback firing for the icons.
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
static int g_icon_cb, g_text_cb;

/* ---- the three icon ids appFw itself uses (namespace 0) ---- */
#define ICON_REC_BIG   0x02000488u   /* 0x0050 x 0x00a4 */
#define ICON_REC_MED   0x02000484u   /* 0x0050 x 0x00a4 */
#define ICON_REC_SMALL 0x020003c7u   /* 0x012c x 0x0042 */

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


/* ---- resource arenas + font loading (same contract as image 645/648) ---- */
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
    if (!add) return 0;
    return add((unsigned char)idx, (const void *)param);
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
    dprintf(2, "FX6_MI647 loadFonts ok=%d/%d\n", ok, total);
}

static int fx6_scan_rect(int x0, int y0, int w, int h, const char *tag)
{
    int n = 0, fx = -1, fy = -1, lx = -1, ly = -1;
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
    }
    dprintf(2, "FX6_MI647 %s nonzero=%d bbox=(%d,%d)-(%d,%d)\n", tag, n, fx, fy, lx, ly);
    return n;
}

/* Icons go through the ImageData path, so this callback is the proof the widget loaded an image. */
static void fx6_icon_image_cb(void *sprite, void *image_data, void *ud)
{
    (void)sprite;
    int dx = ud ? *(int *)((char *)ud + 0x1e8) : 0;
    int dy = ud ? *(int *)((char *)ud + 0x1ec) : 0;
    g_icon_cb++;
    if (!image_data) { dprintf(2, "FX6_MI647 icon cb image=nil at %d,%d\n", dx, dy); return; }
    dprintf(2, "FX6_MI647 icon cb image=%p at %d,%d\n", image_data, dx, dy);
}

static void fx6_text_image_cb(void *sprite, void *image_data, void *ud)
{
    (void)sprite; (void)ud;
    g_text_cb++;
    dprintf(2, "FX6_MI647 text cb image=%p\n", image_data);
}

/* Draw one native view_icon with a real image ResID. */
static void fx6_draw_icon(uint64_t appfw, int x, int y, int w, int h, uint32_t resid, const char *tag)
{
    void *p = calloc(1, 0x800);
    if (!p) { dprintf(2, "FX6_MI647 %s calloc failed\n", tag); return; }
    char param[0x40];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc2c188ULL))(p, param);

    *(int *)((char *)p + 0x1e8) = x;
    *(int *)((char *)p + 0x1ec) = y;
    *(int *)((char *)p + 0x1f0) = w;
    *(int *)((char *)p + 0x1f4) = h;
    *(unsigned char  *)((char *)p + 0x1fc) = 1;      /* enable the image path */
    *(unsigned int   *)((char *)p + 0x20c) = resid;  /* the image ResID       */

    /* clip rect + colour the widget copies into the sprite (defaults are fine, set anyway) */
    *(unsigned short *)((char *)p + 0x204) = (unsigned short)w;
    *(unsigned short *)((char *)p + 0x206) = (unsigned short)h;

    void *sp = (char *)p + 0x550;
    void (*setcb)(void *, void *, void *) = (void (*)(void *, void *, void *))
        dlsym((void *)-1, "_ZN2ux6gfxeng6Sprite20setImageLoadCallbackEPFvPS1_PN5libra9ImageDataEPvES6_");
    if (setcb) setcb(sp, (void *)fx6_icon_image_cb, p);

    dprintf(2, "FX6_MI647 %s icon=%p resid=0x%08x rect=(%d,%d,%d,%d)\n", tag, p, resid, x, y, w, h);

    void **vt = *(void ***)p;
    if (vt && vt[0x158 / 8]) ((void (*)(void *))vt[0x158 / 8])(p);
    else dprintf(2, "FX6_MI647 %s no onDraw\n", tag);

    fx6_scan_rect(x, y, w, h, tag);
}

/* Draw one native view_string from a resource id (proven path from image 648/649). */
static void fx6_draw_text(uint64_t appfw, int x, int y, int w, int h, uint32_t resid, const char *tag)
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

    void *ts = (char *)p + 0xe40;
    void (*setcb)(void *, void *, void *) = (void (*)(void *, void *, void *))
        dlsym((void *)-1, "_ZN2ux6gfxeng10TextSprite20setImageLoadCallbackEPFvPS1_PN5libra9ImageDataEPvES6_");
    if (setcb) setcb(ts, (void *)fx6_text_image_cb, p);

    dprintf(2, "FX6_MI647 %s text=%p resid=0x%08x rect=(%d,%d,%d,%d)\n", tag, p, resid, x, y, w, h);
    void **vt = *(void ***)p;
    if (vt && vt[0x158 / 8]) ((void (*)(void *))vt[0x158 / 8])(p);

    fx6_scan_rect(x, y, w, h, tag);
}

void fx6_model_done(void) { dprintf(2, "FX6_MODEL_NONE\n"); }

void fx6_force_update(void)
{
    g_appfw = fx6_mod_base("_ZN2ux6resmgr15ResourceManager11setDatabaseEPKc");
    void *fb = fx6_map_osd();
    dprintf(2, "FX6_MI647 appfw=%llx fb=%p\n", (unsigned long long)g_appfw, fb);
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
    if (setdb) dprintf(2, "FX6_MI647 setdb=%d\n", setdb("global.xdb"));
    if (setns) dprintf(2, "FX6_MI647 setns=%d\n", setns(5));

    fx6_add_arena(0, 0x100000U, 0x800000U);
    fx6_add_arena(1, 0x080000U, 0x400000U);
    fx6_add_arena(2, 0x080000U, 0x200000U);
    fx6_load_fonts();

    /* three icons at the real status-bar position family, then one caption */
    fx6_draw_icon(g_appfw, 40, 200, 80, 164, ICON_REC_BIG,   "A_icon488");
    fx6_draw_icon(g_appfw, 140, 200, 80, 164, ICON_REC_MED,   "B_icon484");
    fx6_draw_icon(g_appfw, 240, 200, 80, 164, ICON_REC_SMALL, "C_icon3c7");
    fx6_draw_text(g_appfw, 40, 400, 320, 36, 0x02002227u,     "D_text_shooting");

    int (*proccmd)(unsigned int) = (int (*)(unsigned int))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");
    if (proccmd) proccmd(0);

    dprintf(2, "FX6_MI647 done icon_cbs=%d text_cbs=%d\n", g_icon_cb, g_text_cb);
    fx6_scan_osd();
}
