/* fx6_native_menu_tables.h — drive the REAL FX6 menu from appFw's own descriptor tables.
 *
 * Nothing in this header invents a coordinate, a label, a colour or an icon. Every
 * rectangle and every resource id is read out of appFw's .data.rel.ro at runtime,
 * from the same tables the native presenters hand to the container constructor
 * appFw+0xc870bc. If a table pointer is missing or a count is zero, the builder
 * draws nothing rather than substituting made-up values.
 *
 * Provenance (see reports/2026-11-07-fx6-uxengine-init-assist/STATIC-PIPELINE-MAP.md, §638):
 *   container ctor     appFw+0xc870bc(this=x0, const desc* table=x1, u32 count=x2)
 *   RTTI allow-list    appFw+0xc87054(vptr) -> bool   (5 accepted view classes)
 *   descriptor stride  0x48
 *   descriptor fields:
 *     +0x00  void*    prototype widget (global, constructed from .init_array)
 *     +0x08  char*    debug name, e.g. "No20_SETTING_MAIN_STRING"
 *     +0x18  u32      primary text ResID   (0x020023da == "Set")
 *     +0x1c  u32      text-layout ResID    (ns 5, lang_cmn.uxc)
 *     +0x20  u32      flag (1 = visible)
 *     +0x24  u32      font ResID           (ns 3, style_cmn.uxc)
 *     +0x28  u32      secondary font ResID
 *     +0x2c  u32      style flags
 *     +0x30  u32      0x00000ce2 layout constant
 *     +0x34  u32      0x00002ce9 layout constant
 *     +0x38  u16      subtype (unused by ctor)
 *     +0x3a  u16      row id  <-- what the ctor copies into container->rows[i].id
 *     +0x3c  u16 x   +0x3e u16 y   +0x40 u16 w   +0x42 u16 h   (authoring rect)
 *
 * PROVEN vs ASSUMED, keep this boundary honest:
 *   proven   the stride (0x48), the fields read by the ctor (+0x00 prototype, +0x3a row id),
 *            the 121 table addresses/counts, the ResID packing, the content of every field.
 *   assumed  that +0x3c..+0x42 is what positions the widget. `appFw+0xc870bc` reads only
 *            +0x00 and +0x3a; a scan of every `ldrh` of +0x3c/+0x3e/+0x40/+0x42 in .text found
 *            no site that also stores into view+0x1e8..+0x1f4, so the consumer of the rect is
 *            still unidentified. fx6_apply_geometry() therefore applies the table's own rect
 *            (never a hand-written one) but the caller can disable it via
 *            fx6_apply_geometry_enable = 0 if that turns out to be wrong.
 *
 * ResID packing (liblibra sys_getNamespaceID @0x2e8fc):
 *     ns  = (id >> 13) & 0x7ff
 *     idx =  id & 0x1fff
 *     record id inside the container = (ns << 13) | idx
 *   ns 1 string_english.uxc | 2 string_english_2.uxc | 3 style_cmn.uxc (fonts)
 *   ns 5 lang_cmn.uxc       | 6 color_cmn.uxc        | 0 image_00_169.uxc
 */
#ifndef FX6_NATIVE_MENU_TABLES_H
#define FX6_NATIVE_MENU_TABLES_H

#include <stdint.h>

extern int dprintf(int, const char *, ...);

/* ---- verified descriptor tables (appFw-relative), from /private/tmp/fx6_menu_callsites.json ---- */
typedef struct {
    uint32_t table_off;   /* appFw-relative address of the descriptor array */
    uint16_t count;
    uint32_t callsite;    /* appFw-relative presenter call site, for tracing only */
    const char *what;
} fx6_desc_table;

static const fx6_desc_table fx6_desc_tables[] = {
    { 0x2e9e210u,  98, 0xde1158u, "home presenter" },
    { 0x2eaf208u,  17, 0xde19c4u, "setting page 17" },
    { 0x2ea3e50u,  10, 0xde1b3cu, "setting main list" },
    { 0x2e9ad78u,  35, 0xde1ca4u, "setting page 35" },
    { 0x2ea3ce8u,   2, 0xde21a4u, "setting page 2" },
    { 0x2e9c2d8u,   6, 0xdd9954u, "context menu" },
    { 0x2e9c4d0u,   4, 0xddbab0u, "message 4" },
    { 0x2e9c638u,   4, 0xddc6c4u, "message 4b" },
    { 0x2eb2ad8u,   8, 0xddf5d0u, "network set" },
    { 0x2eb2d60u,  10, 0xddb098u, "change message" },
};
#define FX6_DESC_TABLE_N ((int)(sizeof(fx6_desc_tables) / sizeof(fx6_desc_tables[0])))

/* ---- one decoded descriptor ---- */
typedef struct {
    uint8_t  *raw;         /* appFw + table_off + i*0x48 */
    void     *proto;       /* +0x00 prototype widget */
    const char *name;      /* +0x08 debug name */
    uint32_t  text_resid;  /* +0x18 */
    uint32_t  layout_resid;/* +0x1c */
    uint32_t  flag;        /* +0x20 */
    uint32_t  font_resid;  /* +0x24 */
    uint32_t  font2_resid; /* +0x28 */
    uint16_t  row_id;      /* +0x3a */
    uint16_t  x, y, w, h;  /* +0x3c .. +0x42 */
} fx6_desc;

static inline const char *fx6_desc_name(const fx6_desc *d)
{
    return d && d->name ? d->name : "(unnamed)";
}

/* Fill `out` from table `t` entry `i`. Returns 0 if the table is not mapped. */
static inline int fx6_desc_load(uint64_t appfw, const fx6_desc_table *t, int i, fx6_desc *out)
{
    if (!t || !out || i < 0 || i >= (int)t->count) return 0;
    uint8_t *p = (uint8_t *)(uintptr_t)(appfw + t->table_off + (uint64_t)i * 0x48u);
    out->raw = p;
    out->proto        = *(void **)(p + 0x00);
    out->name         = *(const char **)(p + 0x08);
    out->text_resid   = *(uint32_t *)(p + 0x18);
    out->layout_resid = *(uint32_t *)(p + 0x1c);
    out->flag         = *(uint32_t *)(p + 0x20);
    out->font_resid   = *(uint32_t *)(p + 0x24);
    out->font2_resid  = *(uint32_t *)(p + 0x28);
    out->row_id       = *(uint16_t *)(p + 0x3a);
    out->x = *(uint16_t *)(p + 0x3c);
    out->y = *(uint16_t *)(p + 0x3e);
    out->w = *(uint16_t *)(p + 0x40);
    out->h = *(uint16_t *)(p + 0x42);
    return out->proto != 0;
}

/* ResID helpers, matching liblibra sys_getNamespaceID. */
static inline uint32_t fx6_resid_ns(uint32_t id)  { return (id >> 13) & 0x7ffu; }
static inline uint32_t fx6_resid_idx(uint32_t id) { return id & 0x1fffu; }
static inline uint32_t fx6_resid_record(uint32_t id) { return (fx6_resid_ns(id) << 13) | fx6_resid_idx(id); }

/* ---- apply a descriptor to its prototype widget, then let the widget draw itself ---- */

/* onDraw is vtable slot +0x158 (verified for every view_* class). */
static inline void fx6_widget_ondraw(void *w)
{
    if (!w) return;
    void **vt = *(void ***)w;
    if (!vt) return;
    void (*ondraw)(void *) = (void (*)(void *))vt[0x158 / 8];
    if (ondraw) ondraw(w);
}

/* Geometry goes to the same four int32 fields onDraw reads: +0x1e8 x, +0x1ec y,
 * +0x1f0 w, +0x1f4 h. Sizes are u16 in the table and int32 in the object. */
static int fx6_apply_geometry_enable = 1;

static inline void fx6_apply_geometry(void *w, const fx6_desc *d)
{
    if (!w || !d || !fx6_apply_geometry_enable) return;
    *(int32_t *)((char *)w + 0x1e8) = d->x;
    *(int32_t *)((char *)w + 0x1ec) = d->y;
    *(int32_t *)((char *)w + 0x1f0) = d->w;
    *(int32_t *)((char *)w + 0x1f4) = d->h;
}

/* On view_string, +0x200 is the String ResID read through appFw+0xc3b61c and fed to
 * TextSprite::setString(unsigned). On view_fill the same slot is a *colour* ResID
 * (setRectColorResID at 0xc275ec), so what we write depends on the class. */
static inline void fx6_apply_text(void *w, const fx6_desc *d)
{
    if (!w || !d || !d->text_resid) return;
    *(uint32_t *)((char *)w + 0x200) = d->text_resid;
    *(uint8_t  *)((char *)w + 0x1fc) = 1;   /* enable the text/colour path */
}

/* Fill classes need +0x1fc plus a colour; without both they take the mode-3 early exit and
 * nothing is drawn (this is exactly the `fill=0` seen in run cp-bind-8a785b4c). */
static inline void fx6_apply_fill_color(void *w, uint32_t color_resid)
{
    if (!w || !color_resid) return;
    *(uint8_t  *)((char *)w + 0x1fc) = 1;
    *(uint32_t *)((char *)w + 0x200) = color_resid;
}

/* 0x0200a029 / a02a / a02b select left / right / centre in appFw+0xc3b744. */
static inline void fx6_apply_layout(void *w, const fx6_desc *d)
{
    if (!w || !d || !d->layout_resid) return;
    *(uint32_t *)((char *)w + 0x210) = d->layout_resid;
}

/* Several descriptors share the same +0x00 singleton (e.g. 56 of the 98 home-page rows point at
 * the same view_string). Whether the native pages clone a fresh instance per row is not yet
 * proven, so by default we draw each distinct singleton once; set fx6_desc_allow_aliases = 1 to
 * draw every row against the shared object instead. */
static int fx6_desc_allow_aliases = 0;

/* Draw one whole table: apply geometry + text + layout, then onDraw. */
static inline int fx6_draw_desc_table(uint64_t appfw, const fx6_desc_table *t)
{
    if (!t) return 0;
    int drawn = 0;
    void *seen[256];
    int nseen = 0;
    for (int i = 0; i < (int)t->count; i++) {
        fx6_desc d;
        if (!fx6_desc_load(appfw, t, i, &d)) {
            dprintf(2, "FX6_TBL %s [%02d] no prototype, skipped\n", t->what, i);
            continue;
        }
        if (!fx6_desc_allow_aliases) {
            int dup = 0;
            for (int k = 0; k < nseen; k++) if (seen[k] == d.proto) { dup = 1; break; }
            if (dup) {
                dprintf(2, "FX6_TBL %s [%02d] %s shares proto=%p, alias skipped\n",
                        t->what, i, fx6_desc_name(&d), d.proto);
                continue;
            }
            if (nseen < 256) seen[nseen++] = d.proto;
        }
        dprintf(2, "FX6_TBL %s [%02d] %s proto=%p rect=(%d,%d,%d,%d) text=0x%08x font=0x%08x\n",
                t->what, i, fx6_desc_name(&d), d.proto, d.x, d.y, d.w, d.h,
                d.text_resid, d.font_resid);
        fx6_apply_geometry(d.proto, &d);
        fx6_apply_text(d.proto, &d);
        fx6_apply_layout(d.proto, &d);
        fx6_widget_ondraw(d.proto);
        drawn++;
    }
    return drawn;
}

/* Convenience: draw the setting main list, the page the native menu opens on. */
static inline int fx6_draw_setting_main(uint64_t appfw)
{
    return fx6_draw_desc_table(appfw, &fx6_desc_tables[2]);
}

#endif /* FX6_NATIVE_MENU_TABLES_H */
