/*
 * FX6 TextRM / .ltt font assist (static analysis, no QEMU).
 *
 * Derived from:
 *   libux_core.so +0x2c33c  TextRMLayoutEngine::convertAttribute(FontAttributeReader const&,
 *                                                              TextRM_LayoutRecord&, u32&)
 *   libux_core.so +0x2de9c  TextRMSingleTextHandler::lockHandle()   (authoritative createText caller)
 *   libtextrm.so  +0x7760   TextRM_createText
 *   libtextrm.so  +0x7004   TextRM_drawText
 *   libtextrm.so  +0x5f18   TextRM_loadFontByPath
 *   libtextrm.so  +0x6084   TextRM_getNumberOfFont
 *   libtextrm.so  +0x624c   TextRM_createExtendedText
 *
 * Key ABI facts:
 *
 *   int TextRM_createText(const char *utf8,       // x0
 *                         int mode,               // x1, real callers pass 0
 *                         int flags,              // x2, from convertAttribute
 *                         TextRM_LayoutRecord *rec,// x3, REQUIRED in practice
 *                         int limit_width,        // x4, NOT a font id
 *                         void **out_handle);     // x5
 *
 *   int TextRM_drawText(void *text,               // x0 handle
 *                       const short *rect,        // x1 {x,y,w,h}
 *                       void *param,              // x2 must be non-NULL
 *                       int flags);               // x3
 *
 * Passing x3 = 0 makes TextRM_createText fall back to getDefaultLayout(), and the
 * subsequent selectPixelFormat/selectTextColor/getFontStyleHandle find no font, so
 * composeString yields no handle and TextRM_getBounds reports w=h=0.
 * Passing an alcor::FontAttributeWriter* as x3 is wrong: that is a different class.
 */
#ifndef FX6_LTT_FONT_H
#define FX6_LTT_FONT_H

#include <stdint.h>

typedef struct {
    uint32_t font_id;      /* +0x00 resolved font id                   */
    uint32_t encoding;     /* +0x04 always 1                           */
    uint16_t font_size;    /* +0x08 default 20                         */
    uint16_t font_width;   /* +0x0a only when flags bit 0x8            */
    uint32_t pixel_format; /* +0x0c 0 = 16-bit/wide, 1 = 8-bit utf8    */
    uint32_t fore_color;   /* +0x10 ARGB text color                    */
    uint32_t back_color;   /* +0x14 ARGB background                    */
    uint32_t direction;    /* +0x18 0 / 1 / 2                          */
    uint32_t has_edge;     /* +0x1c bool                               */
    uint16_t edge_size;    /* +0x20                                    */
    uint16_t pad0;         /* +0x22                                    */
    uint32_t edge_color;   /* +0x24 ARGB                               */
    uint32_t ellipsis;     /* +0x28 bool                               */
    uint32_t pad1;         /* +0x2c                                    */
    uint32_t pad2[12];     /* +0x30 .. +0x5f                           */
} fx6_textrm_layout_record;

/* Feature mask bits written by convertAttribute. */
#define FX6_ATTR_BASE            0x0001u
#define FX6_ATTR_FONT_WIDTH      0x0008u
#define FX6_ATTR_FORE_COLOR      0x0020u
#define FX6_ATTR_BACK_COLOR      0x0040u
#define FX6_ATTR_EDGE_SIZE_ZERO  0x0100u
#define FX6_ATTR_EDGE_SIZE       0x0300u
#define FX6_ATTR_EDGE_COLOR      0x0400u
#define FX6_ATTR_ELLIPSIS        0x0800u
#define FX6_ATTR_INITIAL         0x0097u

/*
 * Build a record equivalent to what convertAttribute produces for
 * a plain single-line white string with no edge and no background.
 * fontSize defaults to 20 per 0x2c3d8.
 */
static inline void fx6_ltt_record_init(fx6_textrm_layout_record *r,
                                       uint32_t font_id,
                                       uint16_t font_size,
                                       uint32_t fore_argb)
{
    unsigned i;
    for (i = 0; i < sizeof(*r); i++) ((unsigned char *)r)[i] = 0;
    r->font_id      = font_id;
    r->encoding     = 1;              /* 0x2c3c8 */
    r->font_size    = font_size ? font_size : 20;
    r->font_width   = r->font_size;
    r->pixel_format = 1;              /* utf8 */
    r->fore_color   = fore_argb;
    r->back_color   = 0;
    r->direction    = 0;              /* 0x2c430 */
    r->has_edge     = 0;
    r->edge_size    = 0;
    r->edge_color   = 0;
    r->ellipsis     = 0;
}

static inline uint32_t fx6_ltt_flags_for(const fx6_textrm_layout_record *r)
{
    uint32_t f = FX6_ATTR_INITIAL | FX6_ATTR_FORE_COLOR;
    if (r->font_width) f |= FX6_ATTR_FONT_WIDTH;
    if (r->back_color) f |= FX6_ATTR_BACK_COLOR;
    if (r->has_edge)   f |= FX6_ATTR_EDGE_SIZE | FX6_ATTR_EDGE_COLOR;
    return f;
}

/* TextRM_loadFontByPath(path, u16, int, int *out_font_id) -> rc */
typedef int (*fx6_ltt_load_fn)(const char *, unsigned short, int, int *);
/* TextRM_createText -> rc, handle through arg5 */
typedef int (*fx6_ltt_create_fn)(const char *, int, int, void *, int, void **);
/* TextRM_drawText(handle, short rect[4], param, flags) -> rc */
typedef int (*fx6_ltt_draw_fn)(void *, const short *, void *, int);
/* TextRM_getBounds(handle, u16 *w, u16 *h) -> rc */
typedef int (*fx6_ltt_bounds_fn)(void *, unsigned short *, unsigned short *);

/*
 * Full single-line text draw:
 *   rc = create(utf8, 0, flags, &rec, limit_width, &handle)
 *   bounds(handle, &w, &h)
 *   draw(handle, rect, param, 0)
 * Returns the handle, or 0 on failure (rc_out receives the last rc).
 */
static inline void *fx6_ltt_draw_text(fx6_ltt_create_fn  create,
                                      fx6_ltt_bounds_fn  bounds,
                                      fx6_ltt_draw_fn    draw,
                                      const char        *utf8,
                                      uint32_t           font_id,
                                      uint16_t           font_size,
                                      uint32_t           fore_argb,
                                      int                x,
                                      int                y,
                                      int                limit_width,
                                      int               *rc_out)
{
    fx6_textrm_layout_record rec;
    void *handle = 0;
    short rect[4];
    unsigned short w = 0, h = 0;
    int rc;

    if (!create) { if (rc_out) *rc_out = -1; return 0; }

    fx6_ltt_record_init(&rec, font_id, font_size, fore_argb);
    rc = create(utf8, 0, (int)fx6_ltt_flags_for(&rec), &rec, limit_width, &handle);
    if (rc_out) *rc_out = rc;
    if (rc != 0 || !handle) return 0;

    if (bounds) {
        rc = bounds(handle, &w, &h);
        if (rc_out) *rc_out = rc;
    }

    if (draw) {
        rect[0] = (short)x;
        rect[1] = (short)y;
        rect[2] = (short)(w ? w : limit_width);
        rect[3] = (short)(h ? h : font_size);
        rc = draw(handle, rect, 0, 0);
        if (rc_out) *rc_out = rc;
    }
    return handle;
}

/*
 * .ltt font file notes
 *
 * `TextRM_loadFontByPath("/usr/share/app/HeiseiKakuGothW5-SJ_wIcon.ltt", 0, 0, &id)`
 * returned rc=0 and id=6 in run 2b53b09e, so the file is valid and the loader assigns
 * an id. The glyph bitmaps are decoded inside libtextrm/libalcor; a caller does not
 * need to parse the container to render text, only to reuse it with the exact record
 * above. Parsing the .ltt header by hand is therefore not required for menu text.
 *
 * If raw glyph bitmaps are ever needed, the entry point is:
 *   libux_core + 0x2c33c convertAttribute -> record
 *   libux_core + 0x2de9c lockHandle       -> handle
 *   libtextrm  + 0x7004 drawText          -> draws into the active GraphicsDraw target
 */

#endif
