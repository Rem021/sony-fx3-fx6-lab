/* fx6_menu_tree_builder.h — table-driven native FX6 menu (supersedes the hand-placed version)
 *
 * The previous revision of this file placed fills and labels at literal coordinates with
 * literal strings. That produced a menu that only resembled FX6 and is now forbidden.
 * Everything here is read from appFw's own 0x48-byte descriptor tables, so the geometry,
 * the row ids and the resource ids are the native ones.
 *
 * Kept filename on purpose: term_4b286158 already includes this path.
 * The tables, decoders and per-widget appliers live in fx6_native_menu_tables.h.
 *
 * Real class data (unchanged, re-verified with a corrected disassembler):
 *   view_fill              vptr 0x2d1b490  onDraw +0x158 = 0xc2750c  ctor 0xc27800  size 0x1178
 *   view_string            vptr 0x2d1f210  onDraw +0x158 = 0xc3bbd8  ctor 0xc3af98 / 0xc3b0c4
 *   view_icon              vptr 0x2d1bd60  onDraw +0x158 = 0xc2d100  ctor 0xc2c188
 *   view_frame             vptr 0x2d1b660  onDraw +0x158 = 0xc27ea0
 *   view_menu_item         vptr 0x2d1c650  onDraw +0x158 = 0xc35358  ctor 0xc341d4
 *   view_list_scroll_item  vptr 0x2d1c2c0  onDraw +0x158 = 0xc3339c  ctor 0xc30c3c
 *
 * Widget::setParent = appFw+0xb196e0   (PLT-resolved)
 * TextSprite::setString(ResID) = appFw+0xb17680, setString(const char*) = 0xb170f0
 * TextSprite::drawText        = appFw+0xb17a00, freezeDrawText = 0xb17000
 */
#ifndef FX6_MENU_TREE_BUILDER_H
#define FX6_MENU_TREE_BUILDER_H

#include <stdint.h>
#include "fx6_native_menu_tables.h"

extern int dprintf(int, const char *, ...);

/* ---------- optional scratch pool for callers that want their own instances ---------- */
#define FX6_MENU_POOL_SIZE (8UL * 1024UL * 1024UL)
static unsigned char fx6_menu_pool[FX6_MENU_POOL_SIZE] __attribute__((aligned(256)));
static unsigned long fx6_menu_pool_off;

static inline void *fx6_menu_alloc(unsigned long n)
{
    n = (n + 255UL) & ~255UL;
    if (fx6_menu_pool_off + n > FX6_MENU_POOL_SIZE) return 0;
    void *p = fx6_menu_pool + fx6_menu_pool_off;
    fx6_menu_pool_off += n;
    for (unsigned long i = 0; i < n; i++) ((unsigned char *)p)[i] = 0;
    return p;
}

/* ---------- primitive helpers, unchanged semantics ---------- */
static inline void fx6_widget_set_parent(uint64_t appfw, void *child, void *parent)
{
    if (child && parent)
        ((void (*)(void *, void *))(uintptr_t)(appfw + 0xb196e0ULL))(child, parent);
}

static inline void fx6_widget_draw(void *w) { fx6_widget_ondraw(w); }

/* ---------- native page rendering: no coordinates are written by hand ---------- */

/* Draw one of the known native tables by index into fx6_desc_tables[]. */
static inline int fx6_menu_draw_table(uint64_t appfw, int table_index)
{
    if (table_index < 0 || table_index >= FX6_DESC_TABLE_N) return 0;
    return fx6_draw_desc_table(appfw, &fx6_desc_tables[table_index]);
}

/* Draw a table looked up by its appFw-relative address (e.g. 0x2ea3e50 for the setting list). */
static inline int fx6_menu_draw_table_at(uint64_t appfw, uint32_t table_off, uint16_t count)
{
    fx6_desc_table t;
    t.table_off = table_off;
    t.count = count;
    t.callsite = 0;
    t.what = "custom";
    for (int i = 0; i < FX6_DESC_TABLE_N; i++) {
        if (fx6_desc_tables[i].table_off == table_off) {
            t.count = fx6_desc_tables[i].count;
            t.what = fx6_desc_tables[i].what;
            break;
        }
    }
    return fx6_draw_desc_table(appfw, &t);
}

/* Render every known native page. Returns the number of descriptors drawn.
 * This is the "walk the app's own menu tree" entry point: it does not build
 * anything, it renders what appFw already defines. */
static inline int fx6_menu_draw_all(uint64_t appfw)
{
    int total = 0;
    for (int i = 0; i < FX6_DESC_TABLE_N; i++) {
        int n = fx6_draw_desc_table(appfw, &fx6_desc_tables[i]);
        dprintf(2, "FX6_MENU page '%s' drew %d widgets\n", fx6_desc_tables[i].what, n);
        total += n;
    }
    return total;
}

/* Convenience aliases kept so existing call sites keep working. */
static inline int fx6_menu_tree_build(uint64_t appfw, void *screen_parent)
{
    (void)screen_parent;              /* native pages attach to their own presenter parent */
    return fx6_menu_draw_all(appfw);
}

static inline void fx6_menu_tree_draw(void *root)
{
    (void)root;                       /* each widget already drew itself inside fx6_draw_desc_table */
}

#endif /* FX6_MENU_TREE_BUILDER_H */
