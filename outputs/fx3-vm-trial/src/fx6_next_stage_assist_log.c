/* fx6_next_stage_assist.c — native menu tree + GDS (GraphicsContextGRM) shim
 * Static-derived; no QEMU. Link with the 545+ shim.
 *
 * Native context vtable: libgemini-grm.so vtable for gemini::GraphicsContextGRM
 *   vtable = base + 0x1ba68, vptr = vtable + 0x10
 * Slot map (offset from vptr):
 *   0x18 clearBuffer(Color*)
 *   0x20 beginScene(Color*)
 *   0x28 endScene()
 *   0x30 swap()
 *   0x78 setScissorRect(TRect*)
 *   0xf0 setImage(Image*)
 *   0xf8 fillRect(Color*, TRect*)          <- GraphicsDraw::fillRect
 *   0x100 drawImage(Image*, Rect*, Rect*)
 *   0x108 drawImage(Rect*, Rect*)
 *   0x110 drawImage(Rect*, Vector2Fixed32*)
 *   0x118 drawImage(Rect*, Vector2*)
 *   0x120 drawLine(Color*, Vector2Fixed32*, Vector2Fixed32*)
 *   0x128 drawLine(Color*, Vector2*, Vector2*)
 *   0x1e0..0x218 matrix ops
 * Text: no GraphicsContextGRM::drawText. TextRM_drawText -> GraphicsDraw
 *   bitBlit/stretchBlit -> the drawImage slots above (0x100..0x118).
 */
#include "fx6_static_assist.h"
#include "fx6_menu_tree_builder.h"

#define FX6_W 1024
#define FX6_H 540
typedef struct { int16_t x, y; uint16_t w, h; } fx6_rect;
typedef struct { uint8_t r, g, b, a; } fx6_color;

static uint8_t *g_fb;
static int g_fb_ready;

static inline uint32_t fx6_px(const fx6_color *c)
{
    return ((uint32_t)c->r) | ((uint32_t)c->g << 8) |
           ((uint32_t)c->b << 16) | ((uint32_t)c->a << 24);
}

static void shim_fill(void *ctx, const fx6_color *col, const fx6_rect *r)
{
    (void)ctx;
    if (!g_fb || !col || !r) return;
    int x0 = r->x < 0 ? 0 : r->x;
    int y0 = r->y < 0 ? 0 : r->y;
    int x1 = r->x + r->w; if (x1 > FX6_W) x1 = FX6_W;
    int y1 = r->y + r->h; if (y1 > FX6_H) y1 = FX6_H;
    static int nfill; if(nfill++<20) dprintf(2,"FX6_NEXT_FILL n=%d r=%d,%d,%d,%d c=%08x\n",nfill,r->x,r->y,r->w,r->h,fx6_px(col));
    uint32_t px = fx6_px(col);
    for (int y = y0; y < y1; y++) {
        uint32_t *row = (uint32_t *)(g_fb + (unsigned long)y * FX6_W * 4);
        for (int x = x0; x < x1; x++) row[x] = px;
    }
    g_fb_ready = 1;
}

/* Unsupported image/line/text ops are forwarded to the original context so
 * native text/glyph rendering is not replaced by a fake primitive. */
static void *g_orig_image[4];
static void *g_orig_line[2];

static void shim_image0(void *c, void *img, const fx6_rect *s, const fx6_rect *d)
{ static int n; if(n++<10) dprintf(2,"FX6_NEXT_IMG0 s=%d,%d,%d,%d d=%d,%d,%d,%d\n",s?s->x:0,s?s->y:0,s?s->w:0,s?s->h:0,d?d->x:0,d?d->y:0,d?d->w:0,d?d->h:0); if (g_orig_image[0]) ((void(*)(void*,void*,const fx6_rect*,const fx6_rect*))g_orig_image[0])(c,img,s,d); }
static void shim_image1(void *c, const fx6_rect *s, const fx6_rect *d)
{ if (g_orig_image[1]) ((void(*)(void*,const fx6_rect*,const fx6_rect*))g_orig_image[1])(c,s,d); }
static void shim_image2(void *c, const fx6_rect *s, const void *v)
{ if (g_orig_image[2]) ((void(*)(void*,const fx6_rect*,const void*))g_orig_image[2])(c,s,v); }
static void shim_image3(void *c, const fx6_rect *s, const void *v)
{ if (g_orig_image[3]) ((void(*)(void*,const fx6_rect*,const void*))g_orig_image[3])(c,s,v); }
static void shim_line0(void *c, const fx6_color *col, const void *a, const void *b)
{ static int n; if(n++<10) dprintf(2,"FX6_NEXT_LINE0 c=%p a=%p b=%p\n",(void*)col,a,b); if (g_orig_line[0]) ((void(*)(void*,const fx6_color*,const void*,const void*))g_orig_line[0])(c,col,a,b); }
static void shim_line1(void *c, const fx6_color *col, const void *a, const void *b)
{ if (g_orig_line[1]) ((void(*)(void*,const fx6_color*,const void*,const void*))g_orig_line[1])(c,col,a,b); }

static uint64_t fx6_gemini_base(void)
{
    void *sym = dlsym((void *)-1,
        "_ZN6gemini18GraphicsContextGRM8fillRectERKN6stella5ColorERKNS1_5TRectIsEE");
    if (!sym) return 0;
    fx6_dl_info di;
    for (unsigned i = 0; i < sizeof(di); i++) ((char *)&di)[i] = 0;
    if (!dladdr(sym, &di) || !di.dli_fbase) return 0;
    return (uint64_t)(uintptr_t)di.dli_fbase;
}

void fx6_gds_install(void *framebuffer)
{
    g_fb = (uint8_t *)framebuffer;
    uint64_t base = fx6_gemini_base();
    if (!base) { dprintf(2, "FX6_NEXT no gemini-grm\n"); return; }
    uint64_t vtable = base + 0x1ba68ULL;
    uint64_t vptr = vtable + 0x10ULL;
    uint64_t page = vptr & ~0xfffULL;
    mprotect((void *)page, 0x1000, 7);
    void **v = (void **)vptr;
    g_orig_image[0] = v[0x100/8]; g_orig_image[1] = v[0x108/8];
    g_orig_image[2] = v[0x110/8]; g_orig_image[3] = v[0x118/8];
    g_orig_line[0] = v[0x120/8];  g_orig_line[1] = v[0x128/8];
    v[0x0f8/8] = (void *)shim_fill;
    v[0x100/8] = (void *)shim_image0;
    v[0x108/8] = (void *)shim_image1;
    v[0x110/8] = (void *)shim_image2;
    v[0x118/8] = (void *)shim_image3;
    v[0x120/8] = (void *)shim_line0;
    v[0x128/8] = (void *)shim_line1;
    __builtin___clear_cache((char *)vptr, (char *)vptr + 0x138);
    dprintf(2, "FX6_NEXT GDS vtable=%llx fill=%p\n", (unsigned long long)vtable, (void*)shim_fill);
}


void fx6_gds_probe_fill(void)
{
    void *(*get)(void) = (void *(*)(void))dlsym((void *)-1,
        "_ZN2ux4core14GraphicsSystem18getGraphicsContextEv");
    if (!get) { dprintf(2, "FX6_NEXT no getGraphicsContext\n"); return; }
    void *ctx = get();
    if (!ctx) { dprintf(2, "FX6_NEXT ctx=0\n"); return; }
    void **vt = *(void ***)ctx;
    dprintf(2, "FX6_NEXT ctx=%p vt=%p slot31=%p gfb=%p\n", ctx, (void*)vt, vt[0x1f], (void*)g_fb);
    fx6_color col = {255, 0, 0, 255};
    fx6_rect r = {0, 0, 1024, 540};
    if (vt[0x1f]) ((void(*)(void*,const fx6_color*,const fx6_rect*))vt[0x1f])(ctx, &col, &r);
    dprintf(2, "FX6_NEXT probe fill returned\n");
}


/* Correct native draw entry for a view_fill: vt+0x158 = view_fill::onDrawNotice
 * (appFw+0xc27ea0). vt+0x148 is a no-op ret and must not be used for drawing. */
void fx6_native_fill_draw(void *fill)
{
    if (!fill) return;
    void **vt = *(void ***)fill;
    if (!vt) return;
    void (*draw)(void *) = (void (*)(void *))vt[0x158/8];
    uint64_t appfw = fx6_appfw_base_auto();
    uint64_t d = (uint64_t)(uintptr_t)draw;
    int known = appfw && (d == appfw + 0xc2750cULL ||  /* view_fill */
                          d == appfw + 0xc27ea0ULL ||  /* view_frame */
                          d == appfw + 0xc3bbd8ULL ||  /* view_string */
                          d == appfw + 0xc2d100ULL ||  /* view_icon */
                          d == appfw + 0xc35358ULL ||  /* view_menu_item */
                          d == appfw + 0xc3339cULL);   /* view_list_scroll_item */
    dprintf(2, "FX6_NEXT fill_draw p=%p vt=%p draw=%p known=%d\n",
            fill, (void*)vt, (void*)draw, known);
    if (draw && known) draw(fill);
}

/* Create a native view_fill widget (appFw+0xc27800, size 0x1178),
 * set its layout/color fields, and attach it to a native parent widget.
 * This is the non-probe menu panel/border path. */
void *fx6_native_view_fill(uint64_t appfw, void *parent,
                           int x, int y, int w, int h, uint32_t argb)
{
    if (!appfw) return 0;
    void *p = 0;
    extern void *calloc(unsigned long, unsigned long);
    p = calloc(1, 0x1178);
    if (!p) return 0;
    char param[0x40]; for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void(*)(void*, void*))(uintptr_t)(appfw + 0xc27800ULL))(p, param);
    *(int32_t *)((char *)p + 0x1e8) = x;
    *(int32_t *)((char *)p + 0x1ec) = y;
    *(int32_t *)((char *)p + 0x1f0) = w;
    *(int32_t *)((char *)p + 0x1f4) = h;
    *(uint32_t *)((char *)p + 0x1f8) = argb;
    *(uint8_t  *)((char *)p + 0x1fc) = 1;   /* visible */
    *(uint32_t *)((char *)p + 0x21c) = 0;   /* mode 0 */
    *(uint32_t *)((char *)p + 0x220) = 1;   /* alpha/visibility */
    if (parent)
        ((void(*)(void*, void*))(uintptr_t)(appfw + 0xb196e0ULL))(p, parent);
    dprintf(2, "FX6_NEXT view_fill p=%p parent=%p %d,%d %dx%d %08x\n",
            p, parent, x, y, w, h, argb);
    return p;
}


/* Native view_list_scroll_cursor_fixed (appFw+0xc2d874, size 0x239870).
 * Its ctor creates view_fill/view_list_scroll_item children and sets their
 * parents. This is the native list/menu-row carrier, not a probe fill. */
void *fx6_native_list(uint64_t appfw, void *parent)
{
    if (!appfw) return 0;
    void *p = 0;
    extern void *calloc(unsigned long, unsigned long);
    p = calloc(1, 0x239870);
    if (!p) return 0;
    char param[0x40]; for (unsigned i = 0; i < sizeof(param); i++) param[i] = 0;
    ((void(*)(void*, void*))(uintptr_t)(appfw + 0xc2d874ULL))(p, param);
    if (parent)
        ((void(*)(void*, void*))(uintptr_t)(appfw + 0xb196e0ULL))(p, parent);
    dprintf(2, "FX6_NEXT native_list p=%p parent=%p\n", p, parent);
    return p;
}

/* Menu panel: native background + 4 native border fills. */
void *fx6_native_menu_panel(uint64_t appfw, void *parent,
                            int x, int y, int w, int h, uint32_t bg, uint32_t border)
{
    void *root = fx6_native_view_fill(appfw, parent, x, y, w, h, bg);
    fx6_native_view_fill(appfw, root, x, y, w, 2, border);
    fx6_native_view_fill(appfw, root, x, y + h - 2, w, 2, border);
    fx6_native_view_fill(appfw, root, x, y, 2, h, border);
    fx6_native_view_fill(appfw, root, x + w - 2, y, 2, h, border);
    return root;
}


/* Drive the native engine cycle with the correct context gate:
 * gate -> setDirtyRect(win) -> sys_update -> sys_render -> drawFramebuffer.
 * It does not create fake primitives; it renders whatever native tree exists. */
void fx6_native_render_cycle(uint64_t uxengine)
{
    if (!uxengine) return;
    void *ge = fx6_engine_gate(uxengine);
    if (!ge) { dprintf(2, "FX6_NEXT render no engine\n"); return; }
    void *win = (char *)ge + 0xb0;
    fx6_set_window_dirty(win, 0, 0, 1024, 540);
    *(volatile uint8_t *)((char *)win + 0x23c) = 1;

    uint8_t rect[8]; for (unsigned i = 0; i < sizeof(rect); i++) rect[i] = 0;
    ((uint16_t *)rect)[0] = 0; ((uint16_t *)rect)[1] = 0;
    ((uint16_t *)rect)[2] = 1024; ((uint16_t *)rect)[3] = 540;

    void (*setdr)(void *, const void *) =
        (void (*)(void *, const void *))(uintptr_t)(uxengine + 0x7b2d8ULL);
    void (*upd)(void *) = (void (*)(void *))(uintptr_t)(uxengine + 0x82978ULL);
    void (*rend)(void *, const void *) =
        (void (*)(void *, const void *))(uintptr_t)(uxengine + 0x82bd0ULL);
    void (*draw)(void *) = (void (*)(void *))(uintptr_t)(uxengine + 0x839c8ULL);

    setdr(win, rect);
    upd(ge);
    rend(ge, rect);
    draw(ge);
    dprintf(2, "FX6_NEXT render cycle done ge=%p\n", ge);
}


/* Map the real OSD surface directly; GDS shim writes native fills here.
 * Avoids fx6_compat_flush_to_osd / GRM ExternalOSDIF entirely. */
extern int open(const char *, int, ...);
extern void *mmap(void *, unsigned long, int, int, int, long);
extern int close(int);


/* Skip the model wait at appFw+0x1c1e03c. */
void fx6_patch_model_wait(uint64_t appfw)
{
    if (!appfw) return;
    uint64_t pc = appfw + 0x1c1e03cULL;
    uint64_t page = pc & ~0xfffULL;
    mprotect((void *)page, 0x1000, 7);
    uint32_t old = *(uint32_t *)pc;
    *(uint32_t *)pc = 0x52800000U; /* mov w0,#0 */
    __builtin___clear_cache((char *)pc, (char *)pc + 4);
    dprintf(2, "FX6_NEXT model_wait pc=%llx old=%x new=%x\n",
            (unsigned long long)pc, old, *(uint32_t *)pc);
}

void *fx6_map_osd(void)
{
    int fd = open("/dev/mem", 2 /* O_RDWR */);
    if (fd < 0) { dprintf(2, "FX6_NEXT open /dev/mem failed\n"); return 0; }
    void *p = mmap(0, 0x21c000UL, 3 /* RW */, 1 /* SHARED */, fd, 0x41e001000L);
    close(fd);
    if (p == (void *)-1L || !p) { dprintf(2, "FX6_NEXT mmap 41e failed\n"); return 0; }
    g_fb = (uint8_t *)p;
    dprintf(2, "FX6_NEXT osd mapped %p\n", p);
    return p;
}


void fx6_menu_standalone(uint64_t appfw, void *framebuffer)
{
    if (!appfw) return;
    fx6_gds_install(framebuffer);
    int nodes = fx6_menu_tree_build(appfw, 0);
    dprintf(2, "FX6_STANDALONE nodes=%d\n", nodes);
    fx6_menu_tree_draw(0);
    dprintf(2, "FX6_STANDALONE draw done\n");
}

/* Minimal native menu entry point: no model_lock, no presenter wait.
 * Call after the Screen root exists; parent is the Screen/root WidgetBase*. */
void fx6_native_menu_enter(uint64_t appfw, void *screen_root, void *framebuffer)
{
    fx6_model_ready(appfw);
    fx6_engine_gate_auto();
    fx6_gds_install(framebuffer);
    fx6_native_menu_panel(appfw, screen_root,
                          0, 0, FX6_W, FX6_H,
                          0xff101014U, 0xffe0e0e0U);
}
