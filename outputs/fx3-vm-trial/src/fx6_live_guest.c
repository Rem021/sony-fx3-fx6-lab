/* fx6_live_guest.c — Interactive in-guest FX6 native UI controller & renderer
 *
 * Runs inside the ARM64 QEMU guest on AppFw UI thread (tid 222) via fx6_force_update().
 * Renders 100% authentic FX6 pages using real /usr/lib/appFw.so + /usr/lib/libuxengine.so
 * + TextRM + ResourceManager into physical framebuffer 0x41e001000 (gpe0, 1024x540x4).
 *
 * Mailboxes:
 *   0x41df00000: SRM3KYE5 hardware key mailbox (k32[2]=seq, k32[3]=key, k32[6]=ack)
 *   0x41e000f00: FX6M state/page control mailbox:
 *     mb[0] = 0x4658364d ('FX6M')
 *     mb[1] = cmd_seq (incremented by host or guest key handler)
 *     mb[2] = ack_seq (written by guest AFTER gpe0 frame is completely rendered)
 *     mb[3] = page (0=Big6 Home, 1=Three-Layer Menu, 2=Setting Main, 3=Setting Center,
 *                   4=Assignable Button p110, 5=Network Status, 6=HUD Strip,
 *                   7=Clip/Playback, 8=Status/Grid)
 *     mb[4] = sel_box (0..5 on Big6/Center, 0..7 on Setting Main, 0..29 on Assignable)
 *     mb[5] = menu_cat (0..10 for the 11 Three-Layer Menu categories)
 *     mb[6] = menu_item (0..N-1 item index in right column)
 *     mb[7] = menu_depth (0=left category column, 1=right item list, 2=3rd-layer options)
 *     mb[8..13] = cell_val[0..5] (value index for FPS, Shutter, ISO/Gain, ND, WB, Base Look)
 *     mb[14] = rec_fmt_idx (0..4 Rec Format option index)
 *     mb[15] = stats ((text_ok << 24) | (nonzero_pixels & 0x00ffffff))
 */
#include "fx6_static_assist.h"

extern int dprintf(int, const char *, ...);
extern void *fx6_map_osd(void);
extern void fx6_gds_install(void *fb);
extern void fx6_scan_osd(void);
extern void *calloc(unsigned long, unsigned long);
extern void *dlsym(void *, const char *);
extern int open(const char *, int, ...);
extern void *mmap(void *, unsigned long, int, int, int, long);
extern int close(int);
extern int usleep(unsigned int);

#define FX6_DESC_STRIDE  0x48u
#define FX6_COLOR_SEL    0x0200c014u
#define FX6_W            1024
#define FX6_H            540
#define FX6_FB_PIXELS    (FX6_W * FX6_H)
#define FX6_FB_BYTES     (FX6_FB_PIXELS * 4)

static uint64_t g_appfw;
static uint32_t *g_osd;
static int g_text_ok, g_text_n, g_fill_n, g_icon_n, g_skip_n2;

void fx6_model_done(void) {
    dprintf(2, "FX6_MODEL_NONE\n");
}

static int strcmp_(const char *a, const char *b) {
    if (!a || !b) return 1;
    while (*a && *b && *a == *b) { a++; b++; }
    return (int)(unsigned char)*a - (int)(unsigned char)*b;
}

static int strstr_(const char *h, const char *n) {
    if (!h || !n) return 0;
    for (; *h; h++) {
        const char *a = h, *b = n;
        while (*a && *b && *a == *b) { a++; b++; }
        if (!*b) return 1;
    }
    return 0;
}

/* ---------------- native text image -> OSD ------------------------------- */
static int fx6_blit_imagedata_to_osd(void *image, uint32_t *osd, int dst_x, int dst_y) {
    if (!image || !osd) return 0;
    void *(*gd)(void *) = (void *(*)(void *))dlsym((void *)-1, "_ZN5libra9ImageData16sys_getImageDataEv");
    if (!gd) return 0;
    uint8_t *raw = (uint8_t *)gd(image);
    if (!raw) return 0;
    int w = *(uint16_t *)(raw + 0x00);
    int h = *(uint16_t *)(raw + 0x02);
    int pitch_px = (int)(*(uint32_t *)(raw + 0x04));
    void *bmp = *(void **)(raw + 0x18);
    if (!bmp || w <= 0 || h <= 0 || pitch_px <= 0) return 0;
    const uint8_t *bits = *(const uint8_t **)((uint8_t *)bmp + 0x10);
    if (!bits) return 0;
    if (w > 1024) w = 1024;
    int stride = pitch_px * 4;
    int copied = 0;
    for (int y = 0; y < h; y++) {
        int dy = dst_y + y;
        if (dy < 0 || dy >= 540) continue;
        const uint16_t *srow = (const uint16_t *)(bits + (unsigned long)y * (unsigned long)stride);
        uint32_t *drow = osd + (unsigned long)dy * 1024UL;
        for (int x = 0; x < w; x++) {
            int dx = dst_x + x;
            if (dx < 0 || dx >= 1024) continue;
            uint16_t pv = srow[x];
            uint32_t a = (pv & 0xf) * 17u;
            if (a == 0) continue;
            uint32_t r = ((pv >> 12) & 0xf) * 17u;
            uint32_t g = ((pv >>  8) & 0xf) * 17u;
            uint32_t b = ((pv >>  4) & 0xf) * 17u;
            drow[dx] = (a << 24) | (r << 16) | (g << 8) | b;
            copied++;
        }
    }
    return copied;
}

static void fx6_text_image_cb(void *ts, void *image, void *ud) {
    (void)ts;
    int dx = 0, dy = 0;
    if (ud) {
        dx = *(int32_t *)((char *)ud + 0x1e8);
        dy = *(int32_t *)((char *)ud + 0x1ec);
    }
    int n = fx6_blit_imagedata_to_osd(image, g_osd, dx, dy);
    if (n) g_text_ok++;
}

/* ---------------- resources ---------------------------------------------- */
static int fx6_add_arena(int idx, unsigned min, unsigned max) {
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

static void fx6_load_fonts(void) {
    int (*ld)(unsigned int) = (int (*)(unsigned int))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager16sys_loadFontDataEj");
    if (!ld) return;
    int ok = 0, total = 0;
    for (unsigned r = 0x02006000U; r <= 0x0200603fU; r++) { total++; if (ld(r)) ok++; }
    for (unsigned r = 0x0200a000U; r <= 0x0200a02fU; r++) { total++; if (ld(r)) ok++; }
    for (unsigned r = 0x02008000U; r <= 0x0200800fU; r++) { total++; if (ld(r)) ok++; }
    dprintf(2, "FX6_LIVE loadFonts ok=%d/%d\n", ok, total);
}

static int fx6_text_of(uint32_t rid, char *out, unsigned outsz) {
    void (*sc)(void *) = (void (*)(void *))dlsym((void *)-1, "_ZN5libra6StringC1Ev");
    const char *(*pb)(const void *) = (const char *(*)(const void *))dlsym((void *)-1, "_ZNK6stella6String9ptrBufferEv");
    int (*gt)(unsigned, void *) = (int (*)(unsigned, void *))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager7getTextEjRN5libra6StringE");
    out[0] = 0;
    if (!sc || !pb || !gt) return 0;
    unsigned char buf[0x40];
    for (unsigned k = 0; k < sizeof(buf); k++) buf[k] = 0;
    sc(buf);
    int rc = gt(rid, buf);
    const char *s = pb(buf);
    if (rc && s) {
        unsigned n = 0;
        while (s[n] && n + 1 < outsz) { out[n] = s[n]; n++; }
        out[n] = 0;
        return n > 0;
    }
    return 0;
}

static uint32_t fx6_pick(uint32_t a, uint32_t b, const char *want, const char *what) {
    char t[0x60];
    if (fx6_text_of(a, t, sizeof(t)) && want && t[0] && strstr_(t, want)) return a;
    if (fx6_text_of(b, t, sizeof(t)) && want && t[0] && strstr_(t, want)) return b;
    (void)what;
    return a;
}

/* ---------------- native widgets ----------------------------------------- */
static void fx6_render_string_rid(uint64_t appfw, int x, int y, int w, int h,
                                  uint32_t text_resid, const char *tag_name) {
    if (!text_resid || text_resid == 0xffffffffU) return;
    if (w < 8 || h < 4) return;
    void *vs = calloc(1, 0x1400);
    if (!vs) return;
    char param[0x40];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc3af98ULL))(vs, param);

    *(int32_t *)((char *)vs + 0x1e8) = x;
    *(int32_t *)((char *)vs + 0x1ec) = y;
    *(int32_t *)((char *)vs + 0x1f0) = w;
    *(int32_t *)((char *)vs + 0x1f4) = h;
    *(uint32_t *)((char *)vs + 0x200) = text_resid;
    *(uint8_t *)((char *)vs + 0x1fc) = 1;
    *(uint32_t *)((char *)vs + 0x208) = 0x0200600fU;
    *(uint32_t *)((char *)vs + 0x20c) = 0x0200600eU;
    *(uint32_t *)((char *)vs + 0x210) = 0x0200a029U;
    *(uint32_t *)((char *)vs + 0xa14) = 0x0200600bU;
    *(int *)((char *)vs + 0x214) = 0;
    *(int *)((char *)vs + 0x21c) = 1;
    *(int *)((char *)vs + 0x610) = 0;
    *(uint32_t *)((char *)vs + 0xa30) = 0x0200a005U;

    void *ts = (char *)vs + 0xe40;
    void (*setcb)(void *, void *, void *) = (void (*)(void *, void *, void *))
        dlsym((void *)-1, "_ZN2ux6gfxeng10TextSprite20setImageLoadCallbackEPFvPS1_PN5libra9ImageDataEPvES6_");
    if (setcb) setcb(ts, (void *)fx6_text_image_cb, vs);
    *(unsigned short *)((char *)ts + 0xa8) |= 0x0008;

    void **vt = *(void ***)vs;
    if (!vt || !vt[0x158 / 8]) return;
    ((void (*)(void *))vt[0x158 / 8])(vs);

    *(unsigned short *)((char *)ts + 0xa8) |= 0x0006;
    void (*dti)(void *) = (void (*)(void *))dlsym((void *)-1, "_ZN2ux6gfxeng10TextSprite12drawTextImplEv");
    if (dti) dti(ts);
    {
        int (*pc)(unsigned int) = (int (*)(unsigned int))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");
        if (pc) pc(0);
    }
    (void)tag_name;
    g_text_n++;
}

static int fx6_render_string_desc(uint64_t appfw, uint8_t *p) {
    uint32_t text_resid = *(uint32_t *)(p + 0x18);
    uint32_t layout = *(uint32_t *)(p + 0x1c);
    uint32_t font = *(uint32_t *)(p + 0x24);
    uint32_t font2 = *(uint32_t *)(p + 0x28);
    uint32_t d30 = *(uint32_t *)(p + 0x30);
    uint32_t d34 = *(uint32_t *)(p + 0x34);
    uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
    uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
    if (!text_resid || text_resid == 0xffffffffU) return 0;
    if (w < 8 || h < 8) return 0;

    void *vs = calloc(1, 0x1400);
    if (!vs) return 0;
    char param[0x40];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc3af98ULL))(vs, param);

    *(int32_t *)((char *)vs + 0x1e8) = x;
    *(int32_t *)((char *)vs + 0x1ec) = y;
    *(int32_t *)((char *)vs + 0x1f0) = w;
    *(int32_t *)((char *)vs + 0x1f4) = h;
    *(uint32_t *)((char *)vs + 0x200) = text_resid;
    *(uint8_t *)((char *)vs + 0x1fc) = 1;
    *(uint32_t *)((char *)vs + 0x208) = font ? font : 0x0200600fU;
    *(uint32_t *)((char *)vs + 0x20c) = font2 ? font2 : 0x0200600eU;
    *(uint32_t *)((char *)vs + 0x210) = layout ? layout : 0x0200a029U;
    *(uint32_t *)((char *)vs + 0xa14) = 0x0200600bU;
    *(int *)((char *)vs + 0x214) = 0;
    if (d30) *(uint32_t *)((char *)vs + 0x218) = d30;
    *(uint32_t *)((char *)vs + 0x21c) = d34 ? d34 : 1U;
    *(int *)((char *)vs + 0x610) = 0;
    *(uint32_t *)((char *)vs + 0xa30) = 0x0200a005U;

    void *ts = (char *)vs + 0xe40;
    void (*setcb)(void *, void *, void *) = (void (*)(void *, void *, void *))
        dlsym((void *)-1, "_ZN2ux6gfxeng10TextSprite20setImageLoadCallbackEPFvPS1_PN5libra9ImageDataEPvES6_");
    if (setcb) setcb(ts, (void *)fx6_text_image_cb, vs);
    *(unsigned short *)((char *)ts + 0xa8) |= 0x0008;

    void **vt = *(void ***)vs;
    if (!vt || !vt[0x158 / 8]) return 0;
    ((void (*)(void *))vt[0x158 / 8])(vs);

    *(unsigned short *)((char *)ts + 0xa8) |= 0x0006;
    void (*dti2)(void *) = (void (*)(void *))dlsym((void *)-1, "_ZN2ux6gfxeng10TextSprite12drawTextImplEv");
    if (dti2) dti2(ts);
    {
        int (*pc)(unsigned int) = (int (*)(unsigned int))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");
        if (pc) pc(0);
    }
    g_text_n++;
    return 1;
}

static void fx6_fill_rect(uint64_t appfw, int x, int y, int w, int h, uint32_t color_resid) {
    if (w < 1 || h < 1) return;
    void *vf = calloc(1, 0x1180);
    if (!vf) return;
    char param[0x40];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc27698ULL))(vf, param);

    *(int32_t *)((char *)vf + 0x1e8) = x;
    *(int32_t *)((char *)vf + 0x1ec) = y;
    *(int32_t *)((char *)vf + 0x1f0) = w;
    *(int32_t *)((char *)vf + 0x1f4) = h;
    if (color_resid) *(uint32_t *)((char *)vf + 0x200) = color_resid;
    *(uint8_t *)((char *)vf + 0x1fc) = 1;

    void **vt = *(void ***)vf;
    if (!vt) return;
    if (vt[0x148 / 8]) ((void (*)(void *))vt[0x148 / 8])(vf);
    if (!vt[0x158 / 8]) return;
    ((void (*)(void *))vt[0x158 / 8])(vf);

    {
        int (*pc)(unsigned int) = (int (*)(unsigned int))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");
        if (pc) pc(0);
    }
    char *spr = (char *)vf + 0x210;
    char *rects = *(char **)(spr + 0xd0);
    if (rects) {
        float pos[2] = {(float)x, (float)y};
        void (*srp)(void *, unsigned short, const void *) = (void (*)(void *, unsigned short, const void *))
            dlsym((void *)-1, "_ZN2ux6gfxeng6Sprite10setRectPosEtRKNS_4core7Vector2E");
        if (srp) srp(spr, 0, pos);
        else { *(float *)(rects + 0x00) = pos[0]; *(float *)(rects + 0x04) = pos[1]; }
        void (*rr)(void *, const void *, const void *, float, float) = (void (*)(void *, const void *, const void *, float, float))
            dlsym((void *)-1, "_ZN2ux6gfxeng6Sprite10renderRectERKNS_4core7Vector2ERKNS1_8RectDataEff");
        if (rr) rr(spr, pos, rects, 0.0f, 0.0f);
    }
    g_fill_n++;
}

static void fx6_icon_blit(uint64_t appfw, int x, int y, int w, int h, uint32_t img) {
    if (w < 1 || h < 1) return;
    if (!img || img == 0xffffffffU) return;
    void *ic = calloc(1, 0x700);
    if (!ic) return;
    char param[0x40];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc2c188ULL))(ic, param);

    *(int32_t *)((char *)ic + 0x1e8) = x;
    *(int32_t *)((char *)ic + 0x1ec) = y;
    *(int32_t *)((char *)ic + 0x1f0) = w;
    *(int32_t *)((char *)ic + 0x1f4) = h;
    *(uint32_t *)((char *)ic + 0x20c) = img;
    *(uint8_t *)((char *)ic + 0x1fc) = 1;
    *(uint8_t *)((char *)ic + 0x21c) = 0xff;
    *(uint8_t *)((char *)ic + 0x21d) = 0xff;
    *(uint8_t *)((char *)ic + 0x21e) = 0xff;
    *(uint8_t *)((char *)ic + 0x21f) = 0xff;
    *(uint16_t *)((char *)ic + 0x204) = w;
    *(uint16_t *)((char *)ic + 0x206) = h;

    void **vt = *(void ***)ic;
    if (!vt) return;
    if (vt[0x148 / 8]) ((void (*)(void *))vt[0x148 / 8])(ic);
    if (vt[0x158 / 8]) ((void (*)(void *))vt[0x158 / 8])(ic);
    {
        int (*pc)(unsigned int) = (int (*)(unsigned int))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");
        if (pc) pc(0);
    }
    g_icon_n++;
}

static void fx6_border(uint64_t appfw, int x, int y, int w, int h, uint32_t color_resid) {
    if (w < 3 || h < 3) return;
    fx6_fill_rect(appfw, x,         y,         w, 1, color_resid);
    fx6_fill_rect(appfw, x,         y + h - 1, w, 1, color_resid);
    fx6_fill_rect(appfw, x,         y,         1, h, color_resid);
    fx6_fill_rect(appfw, x + w - 1, y,         1, h, color_resid);
}

static int fx6_tag_kind(uint64_t appfw, void *proto) {
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

/* ---------------- Big-6 Cells & Menu Tables ------------------------------ */
typedef struct {
    uint32_t title_rid;
    uint32_t val_rids[7];
    int n_vals;
} fx6_cell_spec_t;

static const fx6_cell_spec_t g_cell_specs[6] = {
    /* 0: FPS */
    { 0x02005082u, { 0x020030ceu, 0x020050a7u, 0x0200532du, 0, 0, 0, 0 }, 3 },
    /* 1: Shutter */
    { 0x020050e8u, { 0x02002fe1u, 0x020030ceu, 0x02002009u, 0, 0, 0, 0 }, 3 },
    /* 2: ISO/Gain */
    { 0x02004c32u, { 0x02005459u, 0x02002063u, 0x020023c2u, 0, 0, 0, 0 }, 3 },
    /* 3: ND Filter */
    { 0x02004288u, { 0x020054fdu, 0x02002090u, 0x020023bdu, 0, 0, 0, 0 }, 3 },
    /* 4: White Bal. */
    { 0x02005689u, { 0x02002934u, 0x02005281u, 0x02002008u, 0, 0, 0, 0 }, 3 },
    /* 5: Base Look */
    { 0x020023f8u, { 0x02002464u, 0x02002460u, 0x020021a0u, 0x0200219eu, 0x020023f1u, 0x020023f5u, 0x020023edu }, 7 },
};

static uint32_t fx6_cell_val_rid(int cell_idx, const uint32_t *cell_vals) {
    if (cell_idx < 0 || cell_idx >= 6) return 0x02002464u;
    int n = g_cell_specs[cell_idx].n_vals;
    uint32_t idx = cell_vals ? (cell_vals[cell_idx] % (uint32_t)n) : 0;
    return g_cell_specs[cell_idx].val_rids[idx];
}

/* Page 0: Big-6 Home (TABLE 0x2e9e210, 98 rows) */
static void render_page_big6_home(uint64_t appfw, uint32_t sel_box, const uint32_t *cell_vals) {
    uint8_t *base = (uint8_t *)(uintptr_t)(appfw + 0x2e9e210ULL);
    int (*proccmd)(unsigned int) = (int (*)(unsigned int))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");

    uint8_t *cell_rows[6];
    int n_cells = 0;

    for (int i = 0; i < 98; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        void *proto = *(void **)p;
        const char *nm = *(const char **)(p + 0x08);
        if (nm && nm[0] == 'N' && nm[1] == 'o' && nm[2] == '2' &&
            nm[3] >= '0' && nm[3] <= '9' && nm[4] >= '0' && nm[4] <= '9' &&
            nm[5] >= '0' && nm[5] <= '9' && nm[6] == '_') {
            g_skip_n2++;
            continue;
        }
        int kind = fx6_tag_kind(appfw, proto);
        uint32_t resid = *(uint32_t *)(p + 0x18);
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);

        if (kind == 2) {
            fx6_fill_rect(appfw, x, y, w, h, resid);
            continue;
        }
        if (kind == 4) {
            fx6_icon_blit(appfw, x, y, w, h, resid);
            continue;
        }
        if (kind == 3) {
            if (i >= 91 && i <= 96 && n_cells < 6) {
                cell_rows[n_cells++] = p;
                continue;
            }
            if (resid && resid != 0xffffffffU)
                fx6_render_string_desc(appfw, p);
            continue;
        }
        if (kind == 1) {
            if (resid && resid != 0xffffffffU) {
                /* If this is the center Base Look string (0x02002464), let it reflect cell_vals[5] */
                if (resid == 0x02002464u && cell_vals) {
                    fx6_render_string_rid(appfw, x, y, w, h, fx6_cell_val_rid(5, cell_vals), "center-look");
                } else {
                    fx6_render_string_desc(appfw, p);
                }
            }
        }
        if (proccmd) proccmd(0);
    }

    /* Sort the 6 outer cells by (y, x) reading order */
    for (int a = 0; a < n_cells; a++) {
        for (int b = a + 1; b < n_cells; b++) {
            uint16_t ya = *(uint16_t *)(cell_rows[a] + 0x3e), xa = *(uint16_t *)(cell_rows[a] + 0x3c);
            uint16_t yb = *(uint16_t *)(cell_rows[b] + 0x3e), xb = *(uint16_t *)(cell_rows[b] + 0x3c);
            if (yb < ya || (yb == ya && xb < xa)) {
                uint8_t *tmp = cell_rows[a];
                cell_rows[a] = cell_rows[b];
                cell_rows[b] = tmp;
            }
        }
    }

    uint32_t glyph = *(uint32_t *)(uintptr_t)(appfw + 0x23be8e0ULL);
    uint32_t active_cell = sel_box % 6u;
    for (int c = 0; c < n_cells; c++) {
        uint8_t *p = cell_rows[c];
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        fx6_fill_rect(appfw, x, y, w, h, 0x0200c008u);
        if (proccmd) proccmd(0);
        fx6_border(appfw, x, y, w, h, ((uint32_t)c == active_cell) ? 0x0200c011u : 0x0200c00eu);
        if (proccmd) proccmd(0);
        fx6_icon_blit(appfw, x + 6, y + 6, 28, 28, glyph);
        if (proccmd) proccmd(0);
        int th = (h * 38) / 100;
        if (th < 18) th = 18;
        fx6_render_string_rid(appfw, x + 36, y + 6, w - 42, th, g_cell_specs[c].title_rid, "cell-title");
        fx6_render_string_rid(appfw, x + 8, y + 6 + th, w - 16, h - th - 10,
                              fx6_cell_val_rid(c, cell_vals), "cell-value");
        if (proccmd) proccmd(0);
    }
}

/* All 11 level-1 categories in the FX6 camera's order */
static const uint32_t g_cats[11] = {
    0x02004208u, /* 0: User           */
    0x02004d4au, /* 1: Edit User Menu */
    0x02002227u, /* 2: Shooting       */
    0x02002228u, /* 3: Project        */
    0x02002493u, /* 4: Paint/Look     */
    0x0200222bu, /* 5: TC/Media       */
    0x02002229u, /* 6: Monitoring     */
    0x020041fbu, /* 7: Audio          */
    0x02004209u, /* 8: Thumbnail      */
    0x0200222au, /* 9: Technical      */
    0x02004203u, /* 10: Maintenance   */
};

static const uint32_t g_cat0_user[6] = {
    0x02004294u, 0x02004d4au, 0x02004264u, 0x02004286u, 0x02004257u, 0x020023c2u,
};
static const uint32_t g_cat1_edituser[5] = {
    0x02004d4bu, 0x02004294u, 0x02004d4au, 0x02004286u, 0x02004264u,
};
static const uint32_t g_cat2_shooting[7] = {
    0x020023c2u, 0x020023bdu, 0x0200215du, 0x020050e8u, 0x02005689u, 0x020023aau, 0x020023b2u,
};
static const uint32_t g_cat3_project[7] = {
    0x020023f8u, 0x0200425fu, 0x02004261u, 0x02004264u, 0x0200425au, 0x02004257u, 0x02004286u,
};
static const uint32_t g_cat4_paint[7] = {
    0x020023f8u, 0x02002464u, 0x02002460u, 0x020021a0u, 0x0200219eu, 0x020023f1u, 0x020023f5u,
};
static const uint32_t g_cat5_tcmedia[7] = {
    0x02004242u, 0x02004243u, 0x02004244u, 0x02004245u, 0x02002244u, 0x02004253u, 0x02004254u,
};
static const uint32_t g_cat6_monitor[7] = {
    0x02004238u, 0x02004236u, 0x02004235u, 0x02004234u, 0x02004239u, 0x0200423au, 0x02004241u,
};
static const uint32_t g_cat7_audio[7] = {
    0x02004232u, 0x02004233u, 0x02004234u, 0x02002192u, 0x02002191u, 0x02003132u, 0x0200429fu,
};
static const uint32_t g_cat8_thumb[7] = {
    0x02004209u, 0x02004ff3u, 0x0200410du, 0x020028e8u, 0x020042c7u, 0x02004fddu, 0x02004ff8u,
};
static const uint32_t g_cat9_tech[7] = {
    0x0200420eu, 0x020050e8u, 0x02004285u, 0x02004212u, 0x02004211u, 0x02005689u, 0x02004229u,
};
static const uint32_t g_cat10_maint[7] = {
    0x0200426bu, 0x0200426cu, 0x0200426du, 0x0200426eu, 0x0200426fu, 0x02004270u, 0x02004291u,
};

static const uint32_t g_opt_baselook[7] = {
    0x02002464u, 0x02002460u, 0x020021a0u, 0x0200219eu, 0x020023f1u, 0x020023f5u, 0x020023edu,
};
static const uint32_t g_opt_recfmt[5] = {
    0x02004987u, 0x02004989u, 0x0200498bu, 0x0200498du, 0x0200498fu,
};

static const uint32_t *fx6_get_cat_items(uint32_t cat, int *out_n) {
    switch (cat % 11u) {
    case 0: *out_n = 6; return g_cat0_user;
    case 1: *out_n = 5; return g_cat1_edituser;
    case 2: *out_n = 7; return g_cat2_shooting;
    case 3: *out_n = 7; return g_cat3_project;
    case 4: *out_n = 7; return g_cat4_paint;
    case 5: *out_n = 7; return g_cat5_tcmedia;
    case 6: *out_n = 7; return g_cat6_monitor;
    case 7: *out_n = 7; return g_cat7_audio;
    case 8: *out_n = 7; return g_cat8_thumb;
    case 9: *out_n = 7; return g_cat9_tech;
    default: *out_n = 7; return g_cat10_maint;
    }
}

/* Page 1: Three-Layer Menu (TABLE 0x2ea02f8, 35 rows) */
static void render_page_three_layer_menu(uint64_t appfw, uint32_t menu_cat, uint32_t menu_item,
                                         uint32_t menu_depth) {
    uint8_t *base = (uint8_t *)(uintptr_t)(appfw + 0x2ea02f8ULL);
    for (int i = 0; i < 35; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void **)p - appfw);
        if (tag != 0x42d5a40u && tag != 0x42d57d0u) continue;
        fx6_fill_rect(appfw, *(uint16_t *)(p + 0x3c), *(uint16_t *)(p + 0x3e),
                      *(uint16_t *)(p + 0x40), *(uint16_t *)(p + 0x42),
                      *(uint32_t *)(p + 0x18));
    }

    uint32_t cat = menu_cat % 11u;
    int win_start = (cat >= 9u) ? 2 : 0;
    int sel_row = (int)cat - win_start;
    const int lx = 62, ly = 56, lw = 494, lh = 462, rows = 9;
    const int rh = lh / rows;

    for (int i = 0; i < rows; i++) {
        int y = ly + i * rh;
        if (i == sel_row) {
            fx6_fill_rect(appfw, lx, y, lw, rh - 3,
                          (menu_depth == 0) ? FX6_COLOR_SEL : 0x0200c00eu);
        }
        fx6_render_string_rid(appfw, lx + 16, y + 8, lw - 32, rh - 10,
                              g_cats[win_start + i], "category");
    }

    int n_items = 0;
    const uint32_t *items = fx6_get_cat_items(cat, &n_items);
    uint32_t title_rid = g_cats[cat];

    if (menu_depth >= 2u) {
        /* 3rd-layer option list (e.g. Base Look or Rec Format) */
        if (cat == 3u) {
            title_rid = fx6_pick(0x0200425fu, 0x020022d2u, "Rec Format", "Rec Format");
            items = g_opt_recfmt;
            n_items = 5;
        } else {
            title_rid = 0x020023f8u; /* Base Look */
            items = g_opt_baselook;
            n_items = 7;
        }
    }

    fx6_render_string_rid(appfw, 568, 62, 280, 36, title_rid, "col-title");
    fx6_icon_blit(appfw, 578, 112, 38, 38, 0x02000154u);
    fx6_render_string_rid(appfw, 622, 112, 326, 40, 0x02004c3eu, "back");

    uint32_t sel_item = (n_items > 0) ? (menu_item % (uint32_t)n_items) : 0;
    for (int i = 0; i < n_items; i++) {
        int y = 163 + i * 51;
        if ((uint32_t)i == sel_item) {
            fx6_fill_rect(appfw, 578, y - 6, 370, 44, FX6_COLOR_SEL);
        }
        fx6_render_string_rid(appfw, 578, y, 370, 40, items[i], "list-item");
    }
}

/* Page 2: Setting Main (TABLE 0x2ea3e50, 10 rows) */
static void render_page_setting_main(uint64_t appfw, uint32_t sel_box, const uint32_t *cell_vals) {
    uint8_t *base = (uint8_t *)(uintptr_t)(appfw + 0x2ea3e50ULL);
    for (int i = 0; i < 10; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        if (fx6_tag_kind(appfw, *(void **)p) == 2) {
            fx6_fill_rect(appfw, *(uint16_t *)(p + 0x3c), *(uint16_t *)(p + 0x3e),
                          *(uint16_t *)(p + 0x40), *(uint16_t *)(p + 0x42),
                          *(uint32_t *)(p + 0x18));
        }
    }
    const int lx = 96, ly = 72, lw = 402, lh = 432, rows = 8;
    const int rh = lh / rows;
    uint32_t active_cat = sel_box % 8u;
    for (int i = 0; i < rows; i++) {
        int y = ly + i * rh;
        if ((uint32_t)i == active_cat) {
            fx6_fill_rect(appfw, lx, y, lw, rh - 3, FX6_COLOR_SEL);
        }
        fx6_render_string_rid(appfw, lx + 20, y + 10, lw - 40, rh - 14, g_cats[i], "setting-cat");
    }
    int n_items = 0;
    const uint32_t *items = fx6_get_cat_items(active_cat, &n_items);
    fx6_render_string_rid(appfw, 519,  95, 305, 32, g_cats[active_cat], "main-string");
    fx6_render_string_rid(appfw, 534, 158, 290, 32, items[0], "setting-item");
    fx6_render_string_rid(appfw, 534, 193, 290, 32, fx6_cell_val_rid(5, cell_vals), "setting-value");
    {
        uint32_t set = fx6_pick(0x020023dau, 0x020047a4u, "Set", "button label");
        static const int bx[4] = {654, 398, 654, 398}, by[4] = {425, 425, 80, 80};
        for (int i = 0; i < 4; i++)
            fx6_render_string_rid(appfw, bx[i] + 30, by[i] + 24, 110, 30, set, "button");
    }
}

/* Page 3: Setting Center (TABLE 0x2eaf208, 17 rows) */
static void render_page_setting_center(uint64_t appfw, uint32_t sel_box, const uint32_t *cell_vals) {
    uint8_t *base = (uint8_t *)(uintptr_t)(appfw + 0x2eaf208ULL);
    for (int i = 1; i <= 10; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        if (fx6_tag_kind(appfw, *(void **)p) != 2) continue;
        uint32_t c = *(uint32_t *)(p + 0x18);
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        if (w < 1 || h < 1) continue;
        fx6_fill_rect(appfw, x, y, w, h, c);
    }
    uint32_t active_cell = sel_box % 6u;
    for (int i = 11; i <= 16; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        if (w < 8 || h < 8) continue;
        int c = i - 11;
        fx6_border(appfw, x, y, w, h, ((uint32_t)c == active_cell) ? 0x0200c011u : 0x0200c00eu);
        fx6_render_string_rid(appfw, x + 8, y + 6, w - 16, 30, g_cell_specs[c].title_rid, "cell-title");
        fx6_render_string_rid(appfw, x + 8, y + 40, w - 16, h - 46, fx6_cell_val_rid(c, cell_vals), "cell-value");
    }
    {
        uint8_t *t = base + 4 * FX6_DESC_STRIDE; /* No7_CENTER_TITLE */
        uint8_t *v = base + 3 * FX6_DESC_STRIDE; /* No8_CENTER_VALUE */
        uint16_t tx = *(uint16_t *)(t + 0x3c), ty = *(uint16_t *)(t + 0x3e);
        uint16_t tw = *(uint16_t *)(t + 0x40), th = *(uint16_t *)(t + 0x42);
        uint16_t vx = *(uint16_t *)(v + 0x3c), vy = *(uint16_t *)(v + 0x3e);
        uint16_t vw = *(uint16_t *)(v + 0x40), vh = *(uint16_t *)(v + 0x42);
        fx6_render_string_rid(appfw, tx, ty, tw, th, g_cell_specs[active_cell].title_rid, "centre-title");
        fx6_render_string_rid(appfw, vx, vy, vw, vh, fx6_cell_val_rid((int)active_cell, cell_vals), "centre-value");
    }
}

/* Page 4: Assignable Button Page 110 (TABLE 0x2eb75f0, 54 rows) */
static const int g_slot_rows[30] = {
    2, 12, 11, 10, 9, 8, 26, 25, 24, 23, 22, 21,
    19, 18, 17, 16, 15, 14, 13, 20, 28, 7, 6, 5,
    4, 3, 32, 31, 29, 27,
};
static const uint32_t g_pool[30] = {
    0x020023c4u, 0x020020d0u, 0x02004288u, 0x0200423du, 0x0200423fu, 0x0200423eu,
    0x020049f5u, 0x0200290au, 0x02004246u, 0x0200425fu, 0x02004261u, 0x02004242u,
    0x02004253u, 0x02004254u, 0x0200425au, 0x02002e6du, 0x02004214u, 0x02004217u,
    0x02004218u, 0x02004285u, 0x02004212u, 0x02004211u, 0x02004210u, 0x02004229u,
    0x0200422au, 0x02004239u, 0x0200423au, 0x02004241u, 0x0200429fu, 0x02004285u,
};

static void render_page_assignable(uint64_t appfw, uint32_t sel_box) {
    uint8_t *base = (uint8_t *)(uintptr_t)(appfw + 0x2eb75f0ULL);
    for (int i = 1; i < 54; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void **)p - appfw);
        if (tag != 0x42d5a40u && tag != 0x42d57d0u) continue;
        fx6_fill_rect(appfw, *(uint16_t *)(p + 0x3c), *(uint16_t *)(p + 0x3e),
                      *(uint16_t *)(p + 0x40), *(uint16_t *)(p + 0x42),
                      *(uint32_t *)(p + 0x18));
    }
    for (int i = 0; i < 54; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void **)p - appfw);
        uint32_t c = *(uint32_t *)(p + 0x18);
        if (!c || c == 0xffffffffU) continue;
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        if (tag == 0x42d57f0u) fx6_render_string_rid(appfw, x, y, w, h, c, "chrome-text");
        else if (tag == 0x42d5a50u) fx6_icon_blit(appfw, x, y, w, h, c);
    }
    uint32_t active_slot = sel_box % 30u;
    for (int s = 0; s < 30; s++) {
        uint8_t *p = base + (uint64_t)g_slot_rows[s] * FX6_DESC_STRIDE;
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        if (w < 8 || h < 8) continue;
        if ((uint32_t)s == active_slot) fx6_fill_rect(appfw, x, y, w, h, FX6_COLOR_SEL);
        fx6_render_string_rid(appfw, x + 14, y + 6, w - 28, h - 10, g_pool[s], "slot-label");
    }
}

/* HUD slot bindings for HUD Strip / Network / Clip / Status pages */
#define VS_ROW_BASE   0x220u
#define VS_ROW_STRIDE 0x5cu
#define VS_ROW_TYPE   (-4)
#define VS_ROW_VALUE  0x54u
#define VS_ROW_COUNT  0x610u
#define VS_TYPE_VALUE 2u

/* Guard against any NULL Dictionary* passed to libra::Dictionary::addRow */
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

typedef struct {
    const char *widget;
    unsigned char mode;
    unsigned int primary;
    unsigned int v1;
    unsigned int v2;
} hud_bind_t;

static const hud_bind_t g_hud[] = {
    {"No30_gain_value",1,0x020020fcu,800,0},
    {"No17_shutter_mode",0,0x02002009u,0,0},
    {"No1014_shutter_mode",0,0x02002009u,0,0},
    {"No58_nd_filter_mode_nd_filter_clear",0,0x02002090u,0,0},
    {"No1050_nd_filter_mode_nd_filter_clear",0,0x02002090u,0,0},
    {"No16_resolution",0,0x020050a1u,0,0},
    {"No13_base_iso",0,0x02002063u,0,0},
    {"No2089_clip_name_with_rec_function",0,0x020050c4u,0,0},
    {"No2066_battery_icon",0,0x0200211fu,0,0},
    {"No18_shutter_value",1,0x0200207cu,180,0},
    {"No1015_shutter_value",1,0x0200207cu,180,0},
    {"No60_nd_filter_value_nd_transmittance",1,0x02002082u,3,0},
    {"No1052_nd_filter_value_nd_transmittance",1,0x02002082u,3,0},
    {"No55_white_balance_value",1,0x0200208eu,5600,0},
    {"No1047_white_balance_value",1,0x0200208eu,3200,0},
    {"No2063_white_balance_value",1,0x0200208eu,5600,0},
    {"No53_iris_value",1,0x02002093u,28,0},
    {"No1045_iris_value",1,0x02002093u,28,0},
    {"No2052_iris_value",1,0x02002093u,28,0},
    {"No2048_sandq_frame_rate",1,0x020020a6u,24,0},
    {"No21_sandq_frame_rate",1,0x020020a6u,24,0},
    {"No2061_gain_value",1,0x020020fcu,800,0},
    {"No2059_shutter_value",1,0x0200207cu,180,0},
    {"No2055_nd_filter_value_nd_transmittance",1,0x02002082u,3,0},
    {"No2065_white_balance_tint",1,0x0200281cu,0,0},
    {"No1048_white_balance_tint",1,0x0200281cu,0,0},
    {"No47_interval_rec_countdown",2,0x0200220cu,59,0},
    {"No1040_interval_rec_countdown",2,0x0200220cu,5,0},
    {"No1109_zoom_ciz_value",2,0x02002a41u,2,0},
    {"No1106_zoom_focal_length",1,0x020021beu,35,0},
    {"No2047_camera_id",0,0x02004c70u,0,0},
    {"No11_imager_scan_mode",0,0x02002106u,0,0},
    {"No4_recstate_string_slot_1st",0,0x02005078u,0,0},
    {"No1004_recstate_string_slot_1st",0,0x02005078u,0,0},
    {"No2_stbystate_slot_1st",0,0x02005079u,0,0},
    {"No6_stbystate_slot_2nd",0,0x02005079u,0,0},
    {"No15_sdi_hdmi_rec_control_recording_status",0,0x020051e7u,0,0},
    {"No2074_media_remain_time_slotb",0,0x020050f6u,0,0},
    {"No2072_media_remain_time_slota",0,0x020050f6u,0,0},
    {"No2075_media_remain_time_unit_slotb",0,0x0200528du,0,0},
    {"No2073_media_remain_time_unit_slota",0,0x0200528du,0,0},
    {"No120_network_speed_wireless_lan_unit",0,0x02002b74u,0,0},
    {"No117_network_speed_wired_lan_unit",0,0x02002b74u,0,0},
    {"No114_network_speed_usb_tethering_unit",0,0x02002b74u,0,0},
    {"No1095_sandq_frame_rate_fixed",0,0x02002847u,0,0},
    {"No1049_white_balance_hold",0,0x02005281u,0,0},
    {"No54_white_balance_mode",0,0x02002008u,0,0},
    {"No29_gain_mode",0,0x02002009u,0,0},
    {"No52_iris_mode",0,0x02002009u,0,0},
    {"No41_CLIP_NAME",0,0x020050c4u,0,0},
    {"No40_CONTENT_NUMBER",0,0x02002385u,0,0},
    {"No14_CODEC_NAME",0,0x02002f1eu,0,0},
    {"No122_PLAYBACK_STATUS_STRING",0,0x020050d1u,0,0},
    {"No15_RESOLUTION",0,0x02002999u,0,0},
    {"No8_FRAME_RATE_UNIT",0,0x0200532du,0,0},
    {"No422_SQ_FRAME_RATE",0,0x020050a7u,0,0},
    {"No421_INT_REC_STATUS",0,0x020050a7u,0,0},
    {"No31_clip_name",0,0x020050c4u,0,0},
    {"No32_video_codec",0,0x02002f1eu,0,0},
    {"No33_video_size",0,0x02002999u,0,0},
    {"No34_video_fps",0,0x0200532du,0,0},
    {"No35_rec_mode",0,0x020050a7u,0,0},
    {"No8_content_num",0,0x02002385u,0,0},
    {"No1023_gain_value",1,0x020020fcu,800,0},
    {"No1022_sandq_frame_rate_value",1,0x020020a6u,24,0},
    {"No2_MSG",0,0x0200554cu,0,0},
    {"No2_CONTEXT",0,0x0200554cu,0,0},
    {"No3_MSG",0,0x0200554cu,0,0},
    {"No3_TEXT",0,0x0200554cu,0,0},
    {"No3_TEXT1",0,0x0200554cu,0,0},
    {"No3_magnificationdebugdisplay",0,0x0200554cu,0,0},
};
#define HUD_N ((int)(sizeof(g_hud) / sizeof(g_hud[0])))

static const hud_bind_t *fx6_hud_for(const char *name) {
    if (!name) return 0;
    for (int i = 0; i < HUD_N; i++)
        if (!strcmp_(g_hud[i].widget, name)) return &g_hud[i];
    return 0;
}

static void fx6_vs_set_vn(void *vs, unsigned idx, unsigned val) {
    if (!*(void **)((char *)vs + 0x1030)) {
        void *dict = calloc(1, 0x80);
        void (*dc)(void *) = (void (*)(void *))dlsym((void *)-1, "_ZN5libra10DictionaryC1Ev");
        if (dict && dc) {
            dc(dict);
            *(void **)((char *)vs + 0x1030) = dict;
        }
    }
    char *row = (char *)vs + VS_ROW_BASE + (unsigned long)idx * VS_ROW_STRIDE;
    *(int *)(row + VS_ROW_TYPE) = (int)VS_TYPE_VALUE;
    *(unsigned *)(row + VS_ROW_VALUE) = val;
    unsigned cnt = *(unsigned *)((char *)vs + VS_ROW_COUNT);
    if (cnt <= idx) *(unsigned *)((char *)vs + VS_ROW_COUNT) = idx + 1u;
}

static void fx6_render_row(uint64_t appfw, uint8_t *p, const char *tag) {
    const char *name = *(const char **)(p + 0x08);
    uint32_t d18 = *(uint32_t *)(p + 0x18);
    uint32_t layout = *(uint32_t *)(p + 0x1c);
    uint32_t font = *(uint32_t *)(p + 0x24);
    uint32_t font2 = *(uint32_t *)(p + 0x28);
    uint32_t d30 = *(uint32_t *)(p + 0x30);
    uint32_t d34 = *(uint32_t *)(p + 0x34);
    uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
    uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
    if (w < 8 || h < 4) return;

    const hud_bind_t *b = fx6_hud_for(name);
    if (!b && (!d18 || d18 == 0xffffffffU)) return;
    if (!b) {
        char probe[0x60];
        if (!fx6_text_of(d18, probe, sizeof(probe))) return;
    }

    void *vs = calloc(1, 0x1400);
    if (!vs) return;
    char param[0x40];
    for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc3af98ULL))(vs, param);

    *(int32_t *)((char *)vs + 0x1e8) = x;
    *(int32_t *)((char *)vs + 0x1ec) = y;
    *(int32_t *)((char *)vs + 0x1f0) = w;
    *(int32_t *)((char *)vs + 0x1f4) = h;
    *(uint32_t *)((char *)vs + 0x208) = font ? font : 0x0200600fU;
    *(uint32_t *)((char *)vs + 0x20c) = font2 ? font2 : 0x0200600eU;
    *(uint32_t *)((char *)vs + 0x210) = layout ? layout : 0x0200a029U;
    *(uint32_t *)((char *)vs + 0xa14) = 0x0200600bU;
    *(int *)((char *)vs + 0x214) = 0;
    if (d30) *(uint32_t *)((char *)vs + 0x218) = d30;
    *(uint32_t *)((char *)vs + 0x21c) = d34 ? d34 : 1U;
    *(uint32_t *)((char *)vs + 0xa30) = 0x0200a005U;

    if (b) {
        if (b->mode == 0) {
            *(uint32_t *)((char *)vs + 0x200) = b->primary;
        } else {
            if (b->primary) *(uint32_t *)((char *)vs + 0x200) = b->primary;
            fx6_vs_set_vn(vs, 0, b->v1);
            if (b->mode == 2) fx6_vs_set_vn(vs, 1, b->v2);
        }
    } else {
        *(uint32_t *)((char *)vs + 0x200) = d18;
    }
    *(uint8_t *)((char *)vs + 0x1fc) = 1;
    *(int *)((char *)vs + 0x610) = (b && b->mode) ? (b->mode == 2 ? 2 : 1) : *(int *)((char *)vs + 0x610);

    void *ts = (char *)vs + 0xe40;
    void (*setcb)(void *, void *, void *) = (void (*)(void *, void *, void *))
        dlsym((void *)-1, "_ZN2ux6gfxeng10TextSprite20setImageLoadCallbackEPFvPS1_PN5libra9ImageDataEPvES6_");
    if (setcb) setcb(ts, (void *)fx6_text_image_cb, vs);
    *(unsigned short *)((char *)ts + 0xa8) |= 0x0008;

    void **vt = *(void ***)vs;
    if (!vt || !vt[0x158 / 8]) return;
    ((void (*)(void *))vt[0x158 / 8])(vs);
    *(unsigned short *)((char *)ts + 0xa8) |= 0x0006;
    void (*dti)(void *) = (void (*)(void *))dlsym((void *)-1, "_ZN2ux6gfxeng10TextSprite12drawTextImplEv");
    if (dti) dti(ts);
    {
        int (*pc)(unsigned int) = (int (*)(unsigned int))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");
        if (pc) pc(0);
    }
    (void)tag;
    g_text_n++;
}

static void page_table(uint64_t appfw, uint32_t off, int count, const char *label, uint32_t sel_box) {
    uint8_t *base = (uint8_t *)(uintptr_t)(appfw + off);
    int n_thumbs = 0, n_btns = 0, n_rows = 0;
    for (int i = 0; i < count; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void **)p - appfw);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        if (tag == 0x42d58f0u && w >= 60 && h >= 40) {
            n_thumbs++;
        } else if ((tag == 0x42d58d0u && w >= 36 && h >= 36 && w < 900) ||
                   (tag == 0x42d5850u && w >= 40 && h >= 24)) {
            n_btns++;
        } else if ((tag == 0x42d57f0u || tag == 0x42d59a0u) && w >= 40 && h >= 18 && w < 960) {
            n_rows++;
        }
    }

    int thumb_idx = 0, btn_idx = 0, row_idx = 0;
    int active_thumb = (n_thumbs > 0) ? (int)((sel_box == 0 ? 11u : sel_box) % (uint32_t)n_thumbs) : -1;
    int active_btn   = (n_btns > 0)   ? (int)(sel_box % (uint32_t)n_btns) : -1;
    int active_row   = (n_btns == 0 && n_thumbs == 0 && n_rows > 0 && sel_box > 0)
                       ? (int)((sel_box - 1u) % (uint32_t)n_rows) : -1;
    int slider_num   = (int)(((sel_box + 5u) % 9u) + 1u);

    for (int i = 0; i < count; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void **)p - appfw);
        uint32_t c = *(uint32_t *)(p + 0x18);
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        if (tag == 0x42d5a40u || tag == 0x42d57d0u) {
            if (c && c != 0xffffffffU)
                fx6_fill_rect(appfw, x, y, w, h, c);
            else if (w >= 400 && h >= 100)
                fx6_fill_rect(appfw, x, y, w, h, 0x0200c003u);
        } else if (tag == 0x42d5a50u && w >= 140 && h >= 32) {
            fx6_fill_rect(appfw, x, y, w, h, 0x0200c003u);
            if (c && c != 0xffffffffU)
                fx6_icon_blit(appfw, x, y, w, h, c);
        } else if (tag == 0x42d58d0u && w >= 36 && h >= 36 && w < 900) {
            fx6_fill_rect(appfw, x, y, w, h, (btn_idx == active_btn && sel_box > 0) ? 0x0200c00eu : 0x0200c008u);
            if (btn_idx == active_btn)
                fx6_border(appfw, x, y, w, h, FX6_COLOR_SEL);
            btn_idx++;
        } else if (tag == 0x42d58f0u && w >= 60 && h >= 40) {
            if (thumb_idx == active_thumb) {
                fx6_fill_rect(appfw, x - 2, y - 2, w + 4, h + 4, FX6_COLOR_SEL);
            }
            fx6_fill_rect(appfw, x, y, w, h, 0x0200c008u);
            thumb_idx++;
        } else if (tag == 0x42d58b0u && w >= 40 && h >= 6) {
            fx6_fill_rect(appfw, x, y, w, h, 0x0200c008u);
            fx6_fill_rect(appfw, x, y, (w * slider_num) / 10, h, 0x0200c013u);
        } else if (tag == 0x42d5930u && w >= 30 && h >= 60) {
            fx6_fill_rect(appfw, x, y, w, h, 0x0200c008u);
            for (int ch = 0; ch < 4; ch++) {
                int bx = x + 8 + ch * 16;
                int bh = (h * (3 + ((ch + (int)sel_box) % 2))) / 5;
                fx6_fill_rect(appfw, bx, y + h - bh - 4, 10, bh, 0x0200c013u);
            }
        } else if (tag == 0x42d5850u && w >= 40 && h >= 24) {
            fx6_fill_rect(appfw, x, y, w, h - 2, (btn_idx == active_btn && sel_box > 0) ? 0x0200c00eu : 0x0200c008u);
            if (btn_idx == active_btn)
                fx6_border(appfw, x, y, w, h - 2, FX6_COLOR_SEL);
            btn_idx++;
        } else if (tag == 0x42d5880u && w >= 40 && w < 600 && h >= 16) {
            fx6_fill_rect(appfw, x, y, w, h, 0x0200c008u);
            fx6_fill_rect(appfw, x + 2, y + 2, ((w - 4) * slider_num) / 10, h - 4, FX6_COLOR_SEL);
        } else if ((tag == 0x42d59e0u || tag == 0x42d5a20u) && w >= 120 && h >= 120) {
            for (int ry = y + 52; ry + 4 < y + h; ry += 52) {
                fx6_fill_rect(appfw, x + 4, ry, w - 8, 2, 0x0200c00bu);
            }
        }
    }
    for (int i = 0; i < count; i++) {
        uint8_t *p = base + (uint64_t)i * FX6_DESC_STRIDE;
        uint32_t tag = (uint32_t)((uint64_t)(uintptr_t)*(void **)p - appfw);
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        if ((tag == 0x42d57f0u || tag == 0x42d59a0u) && w >= 40 && h >= 18 && w < 960) {
            if (row_idx == active_row)
                fx6_border(appfw, x, y, w, h, FX6_COLOR_SEL);
            row_idx++;
        }
        if (tag == 0x42d57f0u || tag == 0x42d59a0u || tag == 0x42d58d0u ||
            tag == 0x42d5850u || tag == 0x42d5840u || tag == 0x42d5960u) {
            fx6_render_row(appfw, p, label);
        } else if (tag == 0x42d5a50u && !(w >= 140 && h >= 32)) {
            uint32_t c = *(uint32_t *)(p + 0x18);
            if (c && c != 0xffffffffU)
                fx6_icon_blit(appfw, x, y, w, h, c);
        }
    }
}

/* ---------------- Frame Cache (32 slots in guest RAM) -------------------- */
#define CACHE_SLOTS 32
typedef struct {
    int valid;
    uint64_t hash;
    int text_ok;
    int fill_n;
    int icon_n;
    uint32_t *pixels;
} fx6_cache_slot_t;

static fx6_cache_slot_t g_cache[CACHE_SLOTS];
static int g_cache_next = 0;

static uint64_t fx6_state_hash(uint32_t page, uint32_t sel_box, uint32_t menu_cat,
                               uint32_t menu_item, uint32_t menu_depth,
                               const uint32_t *cell_vals, uint32_t rec_fmt_idx) {
    uint64_t h = 1469598103934665603ULL;
    h = (h ^ page) * 1099511628211ULL;
    h = (h ^ sel_box) * 1099511628211ULL;
    h = (h ^ menu_cat) * 1099511628211ULL;
    h = (h ^ menu_item) * 1099511628211ULL;
    h = (h ^ menu_depth) * 1099511628211ULL;
    h = (h ^ rec_fmt_idx) * 1099511628211ULL;
    for (int i = 0; i < 6; i++) {
        h = (h ^ cell_vals[i]) * 1099511628211ULL;
    }
    return h;
}

#define FX6_NUM_PAGES 25u

static void fx6_render_dispatch(uint64_t appfw, uint32_t page, uint32_t sel_box,
                                uint32_t menu_cat, uint32_t menu_item, uint32_t menu_depth,
                                const uint32_t *cell_vals, uint32_t rec_fmt_idx) {
    int (*proccmd)(unsigned int) = (int (*)(unsigned int))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");
    uint64_t h = fx6_state_hash(page, sel_box, menu_cat, menu_item, menu_depth, cell_vals, rec_fmt_idx);

    for (int i = 0; i < CACHE_SLOTS; i++) {
        if (g_cache[i].valid && g_cache[i].hash == h && g_cache[i].pixels) {
            for (int px = 0; px < FX6_FB_PIXELS; px++) {
                g_osd[px] = g_cache[i].pixels[px];
            }
            g_text_ok = g_cache[i].text_ok;
            g_fill_n  = g_cache[i].fill_n;
            g_icon_n  = g_cache[i].icon_n;
            return;
        }
    }

    /* Clear gpe0 framebuffer before rendering the new page */
    for (int px = 0; px < FX6_FB_PIXELS; px++) {
        g_osd[px] = 0;
    }
    g_text_ok = 0;
    g_text_n  = 0;
    g_fill_n  = 0;
    g_icon_n  = 0;
    g_skip_n2 = 0;

    uint32_t sub = menu_depth;
    switch (page % FX6_NUM_PAGES) {
    case 0:
        render_page_big6_home(appfw, sel_box, cell_vals);
        break;
    case 1:
        render_page_three_layer_menu(appfw, menu_cat, menu_item, menu_depth);
        break;
    case 2:
        render_page_setting_main(appfw, sel_box, cell_vals);
        break;
    case 3:
        render_page_setting_center(appfw, sel_box, cell_vals);
        break;
    case 4:
        render_page_assignable(appfw, sel_box);
        break;
    case 5:
        if (sub & 1u)
            page_table(appfw, 0x2ea7648u, 176, "net176", sel_box);
        else
            page_table(appfw, 0x2ead870u, 55, "net55", sel_box);
        break;
    case 6:
        page_table(appfw, 0x2e957b0u, 11, "hud9", 0);
        page_table(appfw, 0x2e96608u, 35, "hud11", sel_box);
        page_table(appfw, 0x2e911f0u, 14, "meter", sel_box);
        break;
    case 7:
        page_table(appfw, 0x2eb2ad8u,  8, "clip83", 0);
        page_table(appfw, 0x2eb1890u, 54, "playback", sel_box);
        break;
    case 8:
        if (sub & 1u) {
            page_table(appfw, 0x2ea0d18u, 69, "setgrid69", sel_box);
        } else {
            page_table(appfw, 0x2eb36a8u, 17, "page86", sel_box);
            page_table(appfw, 0x2eb6510u,  7, "grid109", 0);
        }
        break;
    case 9:
        /* Thumbnail Properties (page 18, 0x2e9cef0, 46 rows — 100% Full-Screen) */
        page_table(appfw, 0x2e9cef0u, 46, "thumbprops", sel_box);
        break;
    case 10:
        /* Touch Menu (0x2ea6b08, 19 rows) + Touch List (0x2eb4e00, 19 rows) */
        page_table(appfw, 0x2ea6b08u, 19, "touchmenu", sel_box);
        page_table(appfw, 0x2eb4e00u, 19, "touchlist", 0);
        break;
    case 11:
        /* Settings Subpage (0x2ead0d8, 26 rows) + Toast Confirm (0x2e9deb0, 11 rows) + Gamma Assist (0x2e917d8, 71 rows) */
        page_table(appfw, 0x2ead0d8u, 26, "subpage26", 0);
        page_table(appfw, 0x2e9deb0u, 11, "toast11", sel_box);
        page_table(appfw, 0x2e917d8u, 71, "gamma71", 0);
        break;
    case 12:
        /* 715: Paint / On-Screen Keyboard Text Input Overlay (page 4, 0x2e92c18, 102 rows) */
        page_table(appfw, 0x2e92c18u, 102, "paintoverlay102", sel_box);
        break;
    case 13:
        /* 716: Media Status SSA/SSB/SSP (page 58, 0x2eaad68, 48 rows) or Media Format Confirm (0x2eafdd8, 49 rows) */
        if (sub & 1u)
            page_table(appfw, 0x2eafdd8u, 49, "mediafmt49", sel_box);
        else
            page_table(appfw, 0x2eaad68u, 48, "mediastatus48", sel_box);
        break;
    case 14:
        /* 717: Clip Thumbnail Browser 4x3 Grid (page 12, 0x2e9b798, 39 rows) or Direct Menu List (page 5, 0x2e94c28, 40 rows) */
        if (sub & 1u)
            page_table(appfw, 0x2e94c28u, 40, "pg5direct40", sel_box);
        else
            page_table(appfw, 0x2e9b798u, 39, "clipgrid39", sel_box);
        break;
    case 15:
        /* 718: Status Icon / Radio Button Page (0x2eb44b8, 19 rows) + Date/Time Touch Picker (0x2ea2e48, 16 rows) + HUD Tracking (0x2e95cc0, 20 rows) */
        if ((sub % 3u) == 1u) {
            page_table(appfw, 0x2ea2e48u, 16, "touchdate16", sel_box);
        } else if ((sub % 3u) == 2u) {
            page_table(appfw, 0x2e95cc0u, 20, "hudtrack20", sel_box);
            page_table(appfw, 0x2e959a8u,  7, "pg7hud7", 0);
        } else {
            page_table(appfw, 0x2eb44b8u, 19, "statusicon19", sel_box);
        }
        break;
    case 16:
        /* 723: Full 253-Row Main Viewfinder HUD (page 10, 0x2e96608, 253 rows) + Tracking (0x2e95cc0, 20 rows) + Audio Meter (0x2e911f0, 14 rows) */
        page_table(appfw, 0x2e96608u, 253, "hudmain253", sel_box);
        page_table(appfw, 0x2e95cc0u,  20, "hudtrack20", 0);
        page_table(appfw, 0x2e911f0u,  14, "meter14", sel_box);
        break;
    case 17:
        /* 724: TC / Audio Level Meter / 6-Button Status Dialog (page 11, 0x2e9ad78, 35 rows) */
        page_table(appfw, 0x2e9ad78u, 35, "tcstatus35", sel_box);
        break;
    case 18:
        /* 725: 6-Line Change Message / Firmware Notice Dialog (page 81, 0x2eb2d60, 10 rows) */
        page_table(appfw, 0x2eb2d60u, 10, "changemsg81", sel_box);
        break;
    case 19:
        /* 726: Wireless LAN / SSID Scan List Page (page 43, 0x2ea5560, 11 rows) */
        page_table(appfw, 0x2ea5560u, 11, "wlanscan43", sel_box);
        break;
    case 20:
        /* 727/728: 3-Column Setting List (page 66, 0x2eacdc0, 10 rows) or Numbered Setting List (page 73, 0x2eafac0, 10 rows) */
        if (sub & 1u)
            page_table(appfw, 0x2eafac0u, 10, "setlist73", sel_box);
        else
            page_table(appfw, 0x2eacdc0u, 10, "setlist66", sel_box);
        break;
    case 21:
        /* 729: 2/3-Line OK/Cancel Confirmation Dialog (page 72, 0x2eaf7a8, 10 rows) or Execute/Cancel Dialog (page 93, 0x2eb4a58, 12 rows) */
        if (sub & 1u)
            page_table(appfw, 0x2eb4a58u, 12, "execdlg93", sel_box);
        else
            page_table(appfw, 0x2eaf7a8u, 10, "confirm72", sel_box);
        break;
    case 22:
        /* 730: Split-Pane Setting Value + Aux Info (page 77, 0x2eb1530, 11 rows) or 2nd-Layer Setting Banner (page 112, 0x2eb8760, 11 rows) */
        if (sub & 1u)
            page_table(appfw, 0x2eb8760u, 11, "banner112", sel_box);
        else
            page_table(appfw, 0x2eb1530u, 11, "splitset77", sel_box);
        break;
    case 23:
        /* 731/732: 15-Button 3x5 Menu Grid (page 64, 0x2eac280, 34 rows) or 10-Button 2x5 Media Grid (page 57, 0x2eaa810, 18 rows) */
        if (sub & 1u)
            page_table(appfw, 0x2eaa810u, 18, "mediagrid57", sel_box);
        else
            page_table(appfw, 0x2eac280u, 34, "menugrid64", sel_box);
        break;
    case 24:
        /* Universal Descriptor Table Mode: cell_vals[0]=off1, cell_vals[1]=cnt1, cell_vals[2]=off2, cell_vals[3]=cnt2 */
        if (cell_vals[0] >= 0x02e90000u && cell_vals[0] <= 0x02ebb000u && cell_vals[1] >= 1u && cell_vals[1] <= 260u) {
            page_table(appfw, cell_vals[0], (int)cell_vals[1], "generic1", sel_box);
        }
        if (cell_vals[2] >= 0x02e90000u && cell_vals[2] <= 0x02ebb000u && cell_vals[3] >= 1u && cell_vals[3] <= 260u) {
            page_table(appfw, cell_vals[2], (int)cell_vals[3], "generic2", 0);
        }
        break;
    }
    if (proccmd) proccmd(0);

    /* Store into cache slot */
    int slot = g_cache_next % CACHE_SLOTS;
    g_cache_next++;
    if (!g_cache[slot].pixels) {
        g_cache[slot].pixels = (uint32_t *)calloc(FX6_FB_PIXELS, 4);
    }
    if (g_cache[slot].pixels) {
        for (int px = 0; px < FX6_FB_PIXELS; px++) {
            g_cache[slot].pixels[px] = g_osd[px];
        }
        g_cache[slot].hash    = h;
        g_cache[slot].text_ok = g_text_ok;
        g_cache[slot].fill_n  = g_fill_n;
        g_cache[slot].icon_n  = g_icon_n;
        g_cache[slot].valid   = 1;
    }
}

static uint32_t fx6_count_nonzero(const uint32_t *osd) {
    uint32_t nz = 0;
    for (int i = 0; i < FX6_FB_PIXELS; i++) {
        if (osd[i] != 0) nz++;
    }
    return nz;
}

static void fx6_apply_key(uint32_t key, volatile uint32_t *mb) {
    uint32_t page       = mb[3] % FX6_NUM_PAGES;
    uint32_t sel_box    = mb[4];
    uint32_t menu_cat   = mb[5] % 11u;
    uint32_t menu_item  = mb[6];
    uint32_t menu_depth = mb[7];

    int n_items = 7;
    fx6_get_cat_items(menu_cat, &n_items);
    if (menu_depth >= 2u) {
        n_items = (menu_cat == 3u) ? 5 : 7;
    }

    switch (key) {
    case 1: /* UP */
        if (page == 0u || page == 3u) {
            sel_box = (sel_box >= 3u) ? (sel_box - 3u) : (sel_box + 3u);
        } else if (page == 1u) {
            if (menu_depth == 0u) {
                menu_cat = (menu_cat + 10u) % 11u;
                menu_item = 0u;
            } else {
                menu_item = (menu_item > 0u) ? (menu_item - 1u) : (uint32_t)(n_items - 1);
            }
        } else {
            sel_box = (sel_box > 0u) ? (sel_box - 1u) : 0u;
        }
        break;
    case 2: /* DOWN */
        if (page == 0u || page == 3u) {
            sel_box = (sel_box + 3u) % 6u;
        } else if (page == 1u) {
            if (menu_depth == 0u) {
                menu_cat = (menu_cat + 1u) % 11u;
                menu_item = 0u;
            } else {
                menu_item = (menu_item + 1u) % (uint32_t)n_items;
            }
        } else {
            sel_box = sel_box + 1u;
        }
        break;
    case 3: /* LEFT */
        if (page == 0u || page == 3u) {
            sel_box = (sel_box + 5u) % 6u;
        } else if (page == 1u) {
            if (menu_depth > 0u) {
                menu_depth--;
                menu_item = 0u;
            }
        } else {
            sel_box = (sel_box > 0u) ? (sel_box - 1u) : 0u;
        }
        break;
    case 4: /* RIGHT */
        if (page == 0u || page == 3u) {
            sel_box = (sel_box + 1u) % 6u;
        } else if (page == 1u) {
            if (menu_depth == 0u) {
                menu_depth = 1u;
                menu_item = 0u;
            } else if (menu_depth == 1u) {
                menu_depth = 2u;
                menu_item = 0u;
            }
        } else {
            sel_box = sel_box + 1u;
        }
        break;
    case 5: /* SET */
        if (page == 0u || page == 3u) {
            uint32_t c = sel_box % 6u;
            mb[8 + c] = (mb[8 + c] + 1u) % (uint32_t)g_cell_specs[c].n_vals;
        } else if (page == 1u) {
            if (menu_depth == 0u) {
                menu_depth = 1u;
                menu_item = 0u;
            } else if (menu_depth == 1u) {
                if (menu_cat == 3u && menu_item == 6u) {
                    /* Assignable Button -> jump to Page 4 */
                    page = 4u;
                    sel_box = 0u;
                } else if ((menu_cat == 3u && (menu_item == 0u || menu_item == 1u)) ||
                           (menu_cat == 4u && menu_item == 0u)) {
                    menu_depth = 2u;
                    menu_item = 0u;
                } else if (menu_cat == 4u && menu_item >= 1u && menu_item <= 6u) {
                    mb[8 + 5] = menu_item - 1u;
                } else {
                    menu_depth = 2u;
                    menu_item = 0u;
                }
            } else {
                if (menu_cat == 3u) {
                    mb[14] = menu_item % 5u;
                } else {
                    mb[8 + 5] = menu_item % 7u;
                }
                menu_depth = 1u;
            }
        }
        break;
    case 6: /* BACK */
        if (page == 1u && menu_depth > 0u) {
            menu_depth--;
            menu_item = 0u;
        } else {
            page = 0u;
        }
        break;
    case 7: /* MENU */
        if (page == 1u) {
            page = 0u;
        } else {
            page = 1u;
            menu_depth = 0u;
        }
        break;
    case 8: /* HOME */
        page = 0u;
        break;
    case 9: /* DISP */
        {
            static const uint32_t disp_cycle[12] = { 6, 1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 0 };
            page = disp_cycle[page % FX6_NUM_PAGES];
        }
        break;
    default:
        break;
    }

    mb[3] = page;
    mb[4] = sel_box;
    mb[5] = menu_cat;
    mb[6] = menu_item;
    mb[7] = menu_depth;
    mb[1] = mb[1] + 1u;
}

extern int g_fx6_live_active;

void fx6_force_update(void) {
    g_fx6_live_active = 1;
    g_appfw = fx6_appfw_base_auto();
    void *fb = fx6_map_osd();
    g_osd = (uint32_t *)fb;
    dprintf(2, "FX6_LIVE appfw=%llx fb=%p\n", (unsigned long long)g_appfw, fb);
    if (!g_appfw || !fb) return;

    fx6_gds_install(fb);
    int (*setcwd)(const char *) = (int (*)(const char *))dlsym((void *)-1, "_ZN2ux4core6Kernel23sys_setCurrentDirectoryEPKc");
    int (*setdb)(const char *) = (int (*)(const char *))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager11setDatabaseEPKc");
    int (*setns)(unsigned short) = (int (*)(unsigned short))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager28sys_setFontNameWithNamespaceEt");
    int (*swbank)(unsigned short, unsigned char) = (int (*)(unsigned short, unsigned char))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager10switchBankEth");
    if (setcwd) setcwd("/usr/share/app/");
    if (setdb) dprintf(2, "FX6_LIVE setdb=%d\n", setdb("global.xdb"));
    if (setns) dprintf(2, "FX6_LIVE setns=%d\n", setns(5));
    if (swbank) { swbank(0, 0); swbank(1, 4); swbank(2, 4); }

    /* Large arenas so repeated interactive page renders never exhaust memory */
    fx6_add_arena(0, 0x200000U, 0x4000000U);
    fx6_add_arena(1, 0x100000U, 0x2000000U);
    fx6_add_arena(2, 0x100000U, 0x1000000U);
    fx6_load_fonts();
    fx6_model_ready(g_appfw);
    fx6_engine_gate_auto();

    /* Map physical mailboxes: 0x41df00000 (keys) and 0x41e000e00 (state/control 'FX6L') */
    volatile uint32_t *k32 = 0;
    volatile uint32_t *mb  = 0;
    int mfd = open("/dev/mem", 2 /* O_RDWR */);
    if (mfd >= 0) {
        void *kp = mmap(0, 0x1000UL, 3, 1, mfd, 0x41df00000L);
        if (kp != (void *)-1L && kp) k32 = (volatile uint32_t *)kp;
        void *cp = mmap(0, 0x1000UL, 3, 1, mfd, 0x41e000000L);
        if (cp != (void *)-1L && cp) mb = (volatile uint32_t *)((char *)cp + 0xe00);
        close(mfd);
    }

    uint32_t cell_vals[6] = { 0, 0, 0, 0, 0, 0 };
    if (mb) {
        for (int i = 0; i < 16; i++) mb[i] = 0;
        mb[0] = 0x4658364cu; /* 'FX6L' */
        mb[1] = 1u;          /* cmd_seq */
        mb[2] = 0u;          /* ack_seq */
        mb[3] = 0u;          /* page 0: Big-6 Home */
        mb[4] = 5u;          /* sel_box: Base Look highlighted */
        mb[5] = 2u;          /* menu_cat: Shooting */
        mb[6] = 0u;          /* menu_item */
        mb[7] = 0u;          /* menu_depth */
    }

    /* Pre-warm Page 1 (Three-Layer Menu) and Page 6 (HUD Strip) into guest RAM cache
     * so clicking MENU or DISP in the browser is instantaneous (<25ms)! */
    fx6_render_dispatch(g_appfw, 1u, 5u, 2u, 0u, 0u, cell_vals, 0u);
    fx6_render_dispatch(g_appfw, 6u, 5u, 2u, 0u, 0u, cell_vals, 0u);

    /* Render initial Big-6 Home page */
    fx6_render_dispatch(g_appfw, mb ? mb[3] : 0u, mb ? mb[4] : 5u,
                        mb ? mb[5] : 2u, mb ? mb[6] : 0u, mb ? mb[7] : 0u,
                        cell_vals, mb ? mb[14] : 0u);
    uint32_t nz = fx6_count_nonzero(g_osd);
    if (mb) {
        mb[15] = ((uint32_t)g_text_ok << 24) | (nz & 0x00ffffffu);
        mb[2]  = mb[1];
    }
    dprintf(2, "FX6_LIVE_READY seq=%u page=%u sel=%u cat=%u item=%u depth=%u nz=%u text_ok=%d fill=%d icon=%d\n",
            mb ? mb[2] : 1u, mb ? mb[3] : 0u, mb ? mb[4] : 5u,
            mb ? mb[5] : 2u, mb ? mb[6] : 0u, mb ? mb[7] : 0u,
            nz, g_text_ok, g_fill_n, g_icon_n);
    fx6_scan_osd();

    /* Persistent interactive loop on tid 222 (owns ux::core TLS) */
    while (1) {
        usleep(25000); /* 25ms poll */
        if (k32 && k32[0] == 0x334d5253u && k32[1] == 0x3545594bu) {
            uint32_t kseq = k32[2];
            uint32_t kack = k32[6];
            if (kseq > kack) {
                uint32_t key = k32[3];
                k32[6] = kseq;
                if (mb) fx6_apply_key(key, mb);
            }
        }
        if (mb && mb[0] == 0x4658364cu && mb[1] != mb[2]) {
            uint32_t req_seq = mb[1];
            uint32_t page    = mb[3];
            uint32_t sel_box = mb[4];
            uint32_t cat     = mb[5];
            uint32_t item    = mb[6];
            uint32_t depth   = mb[7];
            uint32_t rec_fmt = mb[14];
            for (int i = 0; i < 6; i++) cell_vals[i] = mb[8 + i];

            fx6_render_dispatch(g_appfw, page, sel_box, cat, item, depth, cell_vals, rec_fmt);
            uint32_t cur_nz = fx6_count_nonzero(g_osd);
            mb[15] = ((uint32_t)g_text_ok << 24) | (cur_nz & 0x00ffffffu);
            mb[2]  = req_seq;
            dprintf(2, "FX6_LIVE_FRAME seq=%u page=%u sel=%u cat=%u item=%u depth=%u nz=%u text_ok=%d fill=%d icon=%d\n",
                    req_seq, page, sel_box, cat, item, depth, cur_nz, g_text_ok, g_fill_n, g_icon_n);
        }
    }
}
