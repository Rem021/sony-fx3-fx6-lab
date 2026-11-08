/*
 * FX6 sprite/text assist (static, no QEMU).
 *
 * libuxengine.so offsets from the nflasha15 FX6 libraries.
 *
 * Sprite::renderRect(this, Vector2 const& pos, RectData const& rd, float, float)
 *   libuxengine + 0x7e064
 *
 * RectData layout (size >= 0x2c):
 *   +0x00 float x        <- final fillRect x (before Sprite origin correction)
 *   +0x04 float y        <- final fillRect y (before Sprite origin correction)
 *   +0x08 float width
 *   +0x0c float height
 *   +0x10 float crop_left
 *   +0x14 float crop_top
 *   +0x18 float crop_right
 *   +0x1c float crop_bottom
 *   +0x20 uint8 flags
 *   +0x21 uint8 flip
 *   +0x22 uint32 color (stella::CColor, 4 bytes)
 *
 * The 0x7e5a8 fillRect path converts sp+0xb8/0xbc to (x,y):
 *   x = rd.x, y = rd.y
 *   w = rd.width, h = rd.height
 * 0x10/0x14 are only UV crop, NOT position. This is why setting
 * +0x10/+0x14 left fillRect at 0,0.
 *
 * Sprite cache fields used by renderRect:
 *   +0x08 float width
 *   +0x0c float height
 *   +0x22 uint32 color
 *   +0x50 float scale_x / +0x54 float scale_y
 *   +0x68 origin/UV data
 *   +0x78 image pointer
 */
#ifndef FX6_SPRITE_TEXT_ASSIST_H
#define FX6_SPRITE_TEXT_ASSIST_H

#include <stdint.h>

typedef struct {
    float x, y, w, h;
    float crop_l, crop_t, crop_r, crop_b;
    uint8_t flags;
    uint8_t flip;
    uint16_t pad;
    uint32_t color;
} fx6_rectdata;

typedef struct { float x, y; } fx6_vec2;

static inline void fx6_sprite_cache_geom(void *sp, float w, float h)
{
    *(float *)((char *)sp + 0x08) = w;
    *(float *)((char *)sp + 0x0c) = h;
}

static inline void fx6_sprite_cache_color(void *sp, uint32_t rgba)
{
    *(uint32_t *)((char *)sp + 0x22) = rgba;
}

static inline void fx6_rectdata_init(fx6_rectdata *rd, float x, float y,
                                     float w, float h, uint32_t rgba)
{
    for (unsigned i = 0; i < sizeof(*rd); i++) ((unsigned char *)rd)[i] = 0;
    rd->x = x;
    rd->y = y;
    rd->w = w;
    rd->h = h;
    rd->color = rgba;
}

/*
 * uxbase = libuxengine load base.
 * sp     = ux::gfxeng::Sprite* (e.g. view_fill+0x1058)
 * The final fillRect x/y comes from rd.x/rd.y; pos is only rotation/origin.
 */
static inline void fx6_sprite_render_rect(uint64_t uxbase, void *sp,
                                          float x, float y, float w, float h,
                                          uint32_t rgba)
{
    fx6_rectdata rd;
    fx6_vec2 pos = {0.0f, 0.0f};
    fx6_rectdata_init(&rd, x, y, w, h, rgba);
    fx6_sprite_cache_geom(sp, w, h);
    fx6_sprite_cache_color(sp, rgba);
    ((void (*)(void *, const fx6_vec2 *, const fx6_rectdata *, float, float))
        (uintptr_t)(uxbase + 0x7e064ULL))(sp, &pos, &rd, 0.0f, 0.0f);
}

/*
 * TextSprite direct path (avoid view_string/MultiLineTextSprite):
 *   TextSprite::TextSprite()        libuxengine + 0x7eb68
 *   TextSprite::setString(char*)    libuxengine + 0x8035c
 *   TextSprite::drawText()          libuxengine + 0x802bc
 *   TextSprite::render(Vector2&)    libuxengine + 0x80c74
 *
 * drawText() is a prepare step: it sets +0xa5=1 and +0xa8|=0x10.
 * render() sees +0xa5==1 and tail-calls vtable+0xe8, the real glyph render.
 * Calling drawText() alone produces no pixels; render() must follow it.
 *
 * TextSprite size: allocate >= 0x400 (fields through +0x100 are used).
 */
static inline void fx6_textsprite_draw(uint64_t uxbase, void *ts,
                                       const char *utf8, float x, float y)
{
    fx6_vec2 pos = {x, y};
    ((void (*)(void *))(uintptr_t)(uxbase + 0x7eb68ULL))(ts);
    ((void (*)(void *, const char *))(uintptr_t)(uxbase + 0x8035cULL))(ts, utf8);
    ((void (*)(void *))(uintptr_t)(uxbase + 0x802bcULL))(ts);
    ((void (*)(void *, const fx6_vec2 *))(uintptr_t)(uxbase + 0x80c74ULL))(ts, &pos);
}

/*
 * Required for TextSprite::drawTextImpl to deliver the rasterized text:
 *   TextSprite::setImageLoadCallback  libuxengine+0x7f970
 *   writes cb to +0x140, userdata to +0x148.
 * TextSprite::onSetTextImage (0x7f8d4) only calls the callback when +0x140
 * is non-null. Without this callback, drawTextImpl succeeds but the
 * generated libra::ImageData is dropped and onRender() is a plain ret.
 */
typedef void (*fx6_text_image_cb)(void *ts, void *image_data, void *userdata);

static inline void fx6_textsprite_set_callback(uint64_t uxbase, void *ts,
                                               fx6_text_image_cb cb, void *ud)
{
    ((void (*)(void *, fx6_text_image_cb, void *))
        (uintptr_t)(uxbase + 0x7f970ULL))(ts, cb, ud);
}

/*
 * Optional font selection:
 *   TextSprite::setFont(unsigned int*, unsigned char) libuxengine + 0x8080c
 * The first pointer is a font id; the second byte is a flag. A default
 * dictionary is used when this is not called.
 */
static inline void fx6_textsprite_set_font(uint64_t uxbase, void *ts,
                                           uint32_t font_id, uint8_t flag)
{
    ((void (*)(void *, uint32_t *, uint8_t))
        (uintptr_t)(uxbase + 0x8080cULL))(ts, &font_id, flag);
}

/*
 * view_string constructors (appFw):
 *   +0xc3af98  ctor(this, Param const*)
 *   +0xc3b0c4  default ctor(this)
 *
 * +0xc3af98 dereferences x1 immediately:
 *   ldr x0,[x1]       -> this+0x1b8
 *   ldr x0,[x1,#8]    -> this+0x1c0
 *   ldr w0,[x1,#0x20] -> this+0x1c8
 * A null x1 SEGVs at +0xc3afc4. A zeroed Param block is safe but leaves
 * layout/style pointers null, so +0xc3b0c4 (default ctor) is preferred
 * unless a real Param is available.
 *
 * view_string sets:
 *   +0xa14 = 0x44 (font size 68)
 *   +0x104c/+0x1050 CColor IDs
 *   +0xe40 MultiLineTextSprite
 *   +0x1fc/+0x1fd/+0x200 state
 */
static inline void fx6_view_string_default(uint64_t appfw, void *vs)
{
    ((void (*)(void *))(uintptr_t)(appfw + 0xc3b0c4ULL))(vs);
}

static inline void fx6_view_string_param(uint64_t appfw, void *vs,
                                         const void *param)
{
    ((void (*)(void *, const void *))(uintptr_t)(appfw + 0xc3af98ULL))(vs, param);
}

#endif

/* ======================================================================
 * Resource-driven view_string render (verified against appFw+0xc3bbd8).
 *
 * The 638 disassembly shows the minimal field set an app is expected to fill:
 *   +0x1e8 x   +0x1ec y   +0x1f0 w   +0x1f4 h     (int32)
 *   +0x1fc = 1                                    (enable the text path)
 *   +0x200 = String ResID                         (-1 means "no resource string")
 *   +0xa30 / +0x208 / +0x20c / +0x210             FontName ResIDs #0..#3
 *   +0x610 = 0                                    (no placeholder rows)
 * +0x1020 LayoutAttribute and +0x1030 Dictionary are filled by the widget itself.
 * onDraw then does createFont -> setFont(arr,6) -> setLineGap/setLineBreakType ->
 * setRect -> setVerticalAlign -> setTextLayout -> setDictionary -> setString(ResID)
 * -> drawText() -> freezeDrawText() -> prefetchTextImage().
 * ====================================================================== */

typedef struct {
    int32_t  x, y, w, h;
    uint32_t string_resid;  /* ns<<13 | idx packed, see fx6_native_menu_tables.h */
    uint32_t font0;         /* +0xa30 */
    uint32_t font1;         /* +0x208 */
    uint32_t font2;         /* +0x20c */
    uint32_t font3;         /* +0x210, e.g. 0x0200a029 */
} fx6_vs_desc;

#define FX6_VS_SIZE 0x1200u

static inline void fx6_view_string_apply(void *vs, const fx6_vs_desc *d)
{
    if (!vs || !d) return;
    *(int32_t  *)((char *)vs + 0x1e8) = d->x;
    *(int32_t  *)((char *)vs + 0x1ec) = d->y;
    *(int32_t  *)((char *)vs + 0x1f0) = d->w;
    *(int32_t  *)((char *)vs + 0x1f4) = d->h;
    *(uint8_t  *)((char *)vs + 0x1fc) = 1;
    *(uint32_t *)((char *)vs + 0x200) = d->string_resid;
    if (d->font0) *(uint32_t *)((char *)vs + 0xa30) = d->font0;
    if (d->font1) *(uint32_t *)((char *)vs + 0x208) = d->font1;
    if (d->font2) *(uint32_t *)((char *)vs + 0x20c) = d->font2;
    if (d->font3) *(uint32_t *)((char *)vs + 0x210) = d->font3;
    *(uint32_t *)((char *)vs + 0x610) = 0;
}

/* Call the real onDraw (vtable +0x158). */
static inline void fx6_view_string_ondraw(void *vs)
{
    if (!vs) return;
    void **vt = *(void ***)vs;
    if (!vt) return;
    void (*ondraw)(void *) = (void (*)(void *))vt[0x158 / 8];
    if (ondraw) ondraw(vs);
}

/* Full path: default ctor (appFw+0xc3b0c4) -> apply -> onDraw.
 * `mem` must be at least FX6_VS_SIZE bytes and zeroed. Returns `mem`. */
static inline void *fx6_view_string_draw_resid(uint64_t appfw, void *mem, const fx6_vs_desc *d)
{
    if (!appfw || !mem || !d) return 0;
    for (unsigned i = 0; i < FX6_VS_SIZE; i++) ((unsigned char *)mem)[i] = 0;
    ((void (*)(void *))(uintptr_t)(appfw + 0xc3b0c4ULL))(mem);
    fx6_view_string_apply(mem, d);
    fx6_view_string_ondraw(mem);
    return mem;
}
