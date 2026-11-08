/* fx6_menu_items_assist.h — second-level menu items and icons, driven by appFw's own dispatch.
 *
 * Everything below is derived from the class-tag factory at appFw+0xc1935c..0xc19784 and from
 * the three classes it instantiates for the menu pages. No coordinate, label or colour is
 * invented here: the caller passes descriptor records that come out of appFw's tables.
 *
 * ---------------------------------------------------------------------------
 * 1. The factory (appFw+0xc1935c) — the missing link between descriptors and widgets
 * ---------------------------------------------------------------------------
 * Before this, `+0x00` looked like a "prototype object". It is not: it is a **16-byte class tag**
 * living in .bss, whose first qword is a vtable pointer and whose +0x08 dword is a creator index.
 * NOTE the index is at tag+0x08, **not** at descriptor+0x08 (descriptor+0x08 is the debug name).
 * The factory reads it like this:
 *
 *     uint8_t *tag = *(uint8_t **)desc;        // desc->+0x00
 *     int      idx = *(int32_t *)(tag + 8);    // creator index
 *     void *obj = creators[idx](capacity, cursor, &out_size, parent, param);
 *
 * `creators` is the 40-entry table at appFw+0x2911720. Each creator is a sized placement-new:
 *
 *     idx 0  -> 0xc2c188  view_icon               size 0x668
 *     idx 1  -> 0xc27698  view_fill               size 0x308    (the real view_fill ctor)
 *     idx 2  -> 0xc3af98  view_string             (param ctor)
 *     idx 3  -> 0xc208d0
 *     idx 4  -> 0xc341d4  view_menu_item
 *     idx 5  -> 0xc27800  view_frame              size 0x1178   (5 nested view_fill at
 *                                                                +0x228/+0x530/+0x838/+0xb40/+0xe48)
 *     idx 6  -> 0xc2d874  view_list_scroll_cursor_fixed
 *     idx 7  -> 0xc2f298  ... idx 39 -> 0xc36bf4   (page-specific wrappers)
 *
 * Correction to the previous revision of this header: 0xc27698 is view_fill, 0xc27800 is
 * view_frame. Both were previously labelled view_fill.
 *
 * ---------------------------------------------------------------------------
 * 2. How the factory wires a descriptor into the new object
 * ---------------------------------------------------------------------------
 * After construction it calls `[vtable+0x140]` (onCreate) and stores the result, then
 * `[vtable+0x148]`, then `[vtable+0x30](0)`. Then it matches the tag's vtable against a fixed
 * list and copies descriptor fields to class-specific offsets:
 *
 *   tag vtable    class                        descriptor fields      target offsets
 *   0x2d1bd60     view_icon                    +0x18                  obj+0x3c
 *                                              +0x1c/+0x20            obj+0x60/+0x64
 *                                              +0x24/+0x28/+0x2c      obj+0x38/+0x3c?/obj+0x6c
 *   0x2d1f210     view_string                  +0x18                  obj+0x30
 *                                              +0x24/+0x28            obj+0x38/+0x3c
 *                                              +0x1c/+0x20            obj+0x40/+0x44
 *                                              +0x2c                  obj+0x844
 *   0x2d1c2c0     view_list_scroll_item        +0x18                  obj+0x60
 *                                              +0x24/+0x28            obj+0x68/+0x6c
 *                                              +0x1c/+0x20            obj+0x70/+0x74
 *                                              +0x2c                  obj+0x874
 *   0x2d1b490     view_fill                    +0x18                  obj+0x30
 *   0x2d1b660     view_frame                   +0x18                  obj+0x4c
 *   ...          others                       +0x24/+0x28, +0x1c/+0x20  obj+0x50../+0x58..
 *
 * Because the tags are 16-byte .bss objects that are filled at runtime, the *only* correct way to
 * use them is to read them out of appFw memory (fx6_tag_of) rather than to hard-code a vtable.
 *
 * ---------------------------------------------------------------------------
 * 3. What actually paints an icon   (view_icon, appFw+0xc2c188 / onDrawNotice 0xc2d100)
 * ---------------------------------------------------------------------------
 *     if (obj->enabled8 == 0   [+0x1fc]  ||  obj->image_resid == -1  [+0x20c]) { draw nothing; }
 *     ...
 *     ResourceManager::getImageOption(obj->image_resid, NULL, 0)          // number of images
 *     ResourceManager::getImageOption(obj->image_resid, &portion, 2)      // portion descriptor
 *     portion is { u16 count, u16 patch_a, u16 patch_b, ... } staged at obj+0x64c/0x64e
 *     Sprite (obj+0x550).setPatchImageCache(patch_a == 1)
 *     then setRectSize from vtable +0x48/+0x50 results, and drawImage with clip from
 *     obj+0x21c..+0x21f (4 bytes RGBA) and size from obj+0x204/0x206 (u16 w, u16 h).
 *
 * So a menu icon needs exactly two things set: `+0x1fc = 1` and `+0x20c = <image ResID>`.
 * appFw itself installs those ids at 0xc1f858 while drawing the status bar:
 * `0x02000488`, `0x02000484` and `0x020003c7`, all namespace 0 -> image_00_169.uxc.
 * Measured from that container (u16 width, u16 height packed in the record's second word):
 *   0x488 / 0x484 -> 0x0050 x 0x00a4   (80 x 164)   payload 0x92b / 0x8bc
 *   0x3c7         -> 0x012c x 0x0042   (300 x 66)   payload 0xdf0
 *   0x2a0 / 0x418 -> 0x002e x 0x0020 and 0x002c x 0x0020, i.e. the small status icons.
 *
 * CORRECTION (round 771): the field stores in the factory are offsets from the *sub-object*
 * returned by vt[0x140], which for every menu class is `obj + 0x1d0`. So the branch that stores
 * at "+0x3c" is really writing `obj + 0x20c` -- i.e. exactly the image ResID slot. Converted:
 *
 *   branch 0 (icon tag)     +0x3c/+0x60/+0x64/+0x6c  ->  obj +0x20c/+0x230/+0x234/+0x23c
 *   branch 1 (string tag)   +0x30/+0x38..48/+0x844  ->  obj +0x200/+0x208..0x218/+0xa14
 *   branch 2 (list item)    +0x60..78/+0x874       ->  obj +0x230..0x248/+0xa44
 *
 * And descriptor +0x18 really does hold image ids for icon rows: measured from
 * image_00_169.uxc, records 0x64a, 0x504, 0x557, 0x544, 0x51c, 0x57d, 0x4df, 0x52a, 0x2a0,
 * 0x418 and 0x247 all exist in the container. So `desc+0x18 -> obj+0x20c` is the image ResID
 * pipeline, confirmed end to end; the earlier "sizing number, not a ResID" note was wrong.
 *
 * ---------------------------------------------------------------------------
 * 4. view_menu_item (ctor 0xc341d4, onDrawNotice 0xc35358)
 * ---------------------------------------------------------------------------
 * onDrawNotice puts 10 child widgets to sleep (loop over obj+0x9738 + i*8, i = 1..9, mode 3),
 * sets its own mode, then dispatches on `obj+0x200` (the item style, 0..15) through the byte
 * table at 0x22765ac:
 *
 *     style  0      -> 0xc34ad4
 *     style  1      -> 0xc34ad4 with w1=1
 *     styles 2,3    -> 0xc34974     plain text row
 *     styles 4..8   -> 0xc352a8     row with an icon slot at obj+0x23c
 *     styles 9..11  -> 0xc34a54     text row, then a 0x32 x 7 glyph run
 *     styles 12,13  -> 0xc34c60
 *     styles 14,15  -> 0xc34ffc
 *
 * Every branch funnels into the shared row renderer `appFw+0xc347b0`:
 *
 *     void row(view *self, int slot_in_w1, const int32_t rect_x2[4],
 *              int a3, int a4, int a5, void *text_in_x6, uint8_t a7, uint8_t a8_on_stack);
 *
 * with the rect built as { 8, 0x1c4, self_height, ... } (derived from the widget, not literal).
 * It reads `self+0x1d0/0x1d8/0x1e0` for the caption and `self+0x228` for the value id.
 */
#ifndef FX6_MENU_ITEMS_ASSIST_H
#define FX6_MENU_ITEMS_ASSIST_H

#include <stdint.h>

extern int dprintf(int, const char *, ...);

/* ---- the 40-entry creator table (appFw+0x2911720) ---- */
#define FX6_CREATOR_TABLE_OFF 0x2911720u
#define FX6_CREATOR_MAX       40

/* Creator indices that matter for menu pages. */
#define FX6_CRE_ICON        0
#define FX6_CRE_FILL        1
#define FX6_CRE_STRING      2
#define FX6_CRE_MENU_ITEM   4
#define FX6_CRE_FRAME       5
#define FX6_CRE_CURSOR_LIST 6

/* Verified constructor of each creator slot (appFw-relative). */
static const uint32_t fx6_creator_ctor[FX6_CREATOR_MAX] = {
    0xc2c188u, 0xc27698u, 0xc3af98u, 0xc208d0u, 0xc341d4u, 0xc27800u, 0xc2d874u, 0xc2f298u,
    0xc24bf4u, 0xc1fa7cu, 0xc392dcu, 0xc3a2c0u, 0xc24370u, 0xc39f78u, 0xc26294u, 0xc3cc9cu,
    0xc245f4u, 0xc3c510u, 0xc39984u, 0xc26d80u, 0xc3d120u, 0xc20674u, 0xc356a8u, 0xc3e184u,
    0xc1f1d4u, 0xc37f28u, 0xc35e98u, 0xc38710u, 0xc36ae4u, 0xc362c0u, 0xc36cdcu, 0xc36ec8u,
    0xc379acu, 0xc37870u, 0xc36174u, 0xc380b4u, 0xc384ecu, 0xc35fccu, 0xc3824cu, 0xc36bf4u,
};

/* ---- class tags: read them from appFw memory, never hard-code the vtable ---- */
typedef struct {
    uint64_t tag_off;   /* appFw-relative address of the 16-byte tag in .bss */
    const char *name;
} fx6_class_tag;

#define FX6_TAG_VIEW_ICON   0x42d5a50u
#define FX6_TAG_VIEW_STRING 0x42d57f0u
#define FX6_TAG_MENU_ITEM   0x42d58d0u

static inline uint32_t fx6_tag_vtable(uint64_t appfw, uint64_t tag_off)
{
    return *(uint32_t *)(uintptr_t)(appfw + tag_off);
}

static inline int32_t fx6_tag_creator_idx(uint64_t appfw, uint64_t tag_off)
{
    return *(int32_t *)(uintptr_t)(appfw + tag_off + 8);
}

/* The factory's own dispatch: instantiate the class named by the descriptor's +0x00 tag.
 * `desc` is appFw+table_off+i*0x48. Returns the new widget or 0. */
static inline void *fx6_menu_instantiate(uint64_t appfw, const uint8_t *desc,
                                         void *arena, uint32_t *cursor_io,
                                         void *parent, void *param)
{
    if (!appfw || !desc) return 0;
    uint64_t tag = *(const uint64_t *)(const void *)desc;   /* descriptor +0x00 */
    if (!tag) return 0;
    int32_t idx = *(int32_t *)(uintptr_t)(tag + 8);          /* tag +0x08, not desc+0x08 */
    if (idx < 0 || idx >= FX6_CREATOR_MAX) {
        dprintf(2, "FX6_MI bad creator idx=%d tag=0x%llx\n", idx, (unsigned long long)tag);
        return 0;
    }
    uint32_t ctor_off = fx6_creator_ctor[idx];
    /* Signature of every creator: (u32 capacity, void *cursor, u32 *size, void *parent, void *param) */
    void *(*fn)(uint32_t, void *, uint32_t *, void *, void *) =
        (void *(*)(uint32_t, void *, uint32_t *, void *, void *))
        (uintptr_t)(appfw + ctor_off);

    /* Reproduce the sized-allocation contract: the creator writes the object at
     * arena + *cursor_io and advances *cursor_io by the class size it in turn writes back. */
    uint32_t cap = 0x40000u;
    uint32_t out_size = 0;
    uint8_t *dst = (uint8_t *)arena + (cursor_io ? *cursor_io : 0);
    void *obj = fn(cap, dst, &out_size, parent, param);
    if (cursor_io) *cursor_io += out_size;
    dprintf(2, "FX6_MI instantiate idx=%d ctor=0x%x obj=%p size=0x%x\n",
            idx, ctor_off, obj, out_size);
    return obj;
}

/* ---- view_frame: ctor 0xc27800 carves five nested view_fill children ----
 * A frame is therefore the cheapest way to get a bordered panel: one object gives you the
 * background plus four edge fills, all constructed by appFw itself. */
#define FX6_FRAME_CHILD_0 0x228u
#define FX6_FRAME_CHILD_1 0x530u
#define FX6_FRAME_CHILD_2 0x838u
#define FX6_FRAME_CHILD_3 0xb40u
#define FX6_FRAME_CHILD_4 0xe48u

static inline void *fx6_frame_child(void *frame, uint32_t child_off)
{
    return frame ? (void *)((char *)frame + child_off) : 0;
}

/* ---- view_icon: the two fields that make it paint ---- */
/* Virtual-slot reality, measured (relocations applied):
 *
 *   GOT holds X; the ctor stores X+0x10 as the object's vptr, so `ldr x2,[x0,#0x158]` reads
 *   X+0x10+0x158. Reading X+0x158 by mistake yields the *next* slot -- that is how a table can
 *   end up looking like "0x148 is onDraw" or "onDraw is a ret".
 *
 *   Nonzero slots only (everything else in 0..0x15f is zero until the widget system patches it):
 *     view_icon      vptr 0x2d1bd60:  +0x000 0xc2cfb4  +0x008 0xc2d008  +0x0f8 0xc2cec4
 *                                     +0x140 0xc2bfd4  +0x148 0xc2c044  +0x150 0xc2c02c  +0x158 0xc2d100
 *     view_string    vptr 0x2d1f210:  +0x000 0xc3ba18  +0x008 0xc3baf0  +0x0f8 0xc3b264
 *                                     +0x140 0xc3ab34  +0x148 0xc3ae08  +0x150 0xc3af68  +0x158 0xc3bbd8
 *     view_menu_item vptr 0x2d1c650:  +0x000 0xc350a4  +0x008 0xc35168
 *                                     +0x140 0xc34034  +0x148 0xc34080  +0x150 0xc34180  +0x158 0xc35358
 *     view_fill      vptr 0x2d1b490:  +0x000 0xc27724  +0x008 0xc2776c
 *                                     +0x140 0xc27408  +0x148 0xc27448  +0x150 0xc273f8  +0x158 0xc2750c
 *
 *   +0x000 = complete-object dtor, +0x008 = deleting dtor (0xc2d004 stores 0x2d1bd60 back into
 *   [x0], which confirms the X+0x10 vptr frame).
 *   Every menu class returns `this + 0x1d0` from +0x140, which is why the factory's field stores
 *   are sub-object relative. */
static inline void fx6_icon_set_image(void *icon, uint32_t image_resid)
{
    if (!icon) return;
    *(uint8_t  *)((char *)icon + 0x1fc) = 1;        /* enable */
    *(uint32_t *)((char *)icon + 0x20c) = image_resid;
}

static inline void fx6_icon_set_rect(void *icon, int x, int y, int w, int h)
{
    if (!icon) return;
    *(int32_t *)((char *)icon + 0x1e8) = x;
    *(int32_t *)((char *)icon + 0x1ec) = y;
    *(int32_t *)((char *)icon + 0x1f0) = w;
    *(int32_t *)((char *)icon + 0x1f4) = h;
}

/* Icon ids appFw itself installs at 0xc1f858 while drawing the status bar /
 * recording indicator (namespace 0 -> image_00_169.uxc).
 * Measured record headers from the container: 0x488 and 0x484 both carry 0x0050 x 0x00a4,
 * 0x3c7 carries 0x012c x 0x0042; payload lengths 0x92b / 0x8bc / 0xdf0 respectively. */
#define FX6_ICON_RESID_A 0x02000488u
#define FX6_ICON_RESID_B 0x02000484u
#define FX6_ICON_RESID_C 0x020003c7u

/* ---- view_menu_item: style selector + the fields the row renderer consumes ---- */
static inline void fx6_menu_item_set_style(void *item, uint32_t style)
{
    if (!item) return;
    *(uint32_t *)((char *)item + 0x200) = style & 0xfu;
}

static inline void fx6_menu_item_set_rect(void *item, int x, int y, int w, int h)
{
    if (!item) return;
    *(int32_t *)((char *)item + 0x1e8) = x;
    *(int32_t *)((char *)item + 0x1ec) = y;
    *(int32_t *)((char *)item + 0x1f0) = w;
    *(int32_t *)((char *)item + 0x1f4) = h;
}

/* The caption/value ids the row renderer reads (self+0x1d0/+0x1d8/+0x1e0/+0x228). */
static inline void fx6_menu_item_set_text_ids(void *item, uint32_t caption_resid,
                                              uint32_t value_resid)
{
    if (!item) return;
    *(uint32_t *)((char *)item + 0x1d0) = caption_resid;
    *(uint32_t *)((char *)item + 0x1e0) = value_resid;
    /* +0x228 is the "has value" flag read at 0xc349a8 / 0xc352dc */
    *(uint32_t *)((char *)item + 0x228) = value_resid ? 1u : 0u;
}

/* Tab into the icon slot of the "row with icon" styles (4..8). */
static inline void *fx6_menu_item_icon_slot(void *item)
{
    if (!item) return 0;
    return (void *)((char *)item + 0x23c);
}

static inline void fx6_widget_ondraw_generic(void *w)
{
    if (!w) return;
    void **vt = *(void ***)w;
    if (!vt) return;
    void (*ondraw)(void *) = (void (*)(void *))vt[0x158 / 8];
    if (ondraw) ondraw(w);
}

/* Style -> the handler offset onDrawNotice would jump to (0x22765ac byte table). */
static const uint8_t fx6_menu_style_delta[16] = {
    0x00, 0x20, 0x22, 0x22, 0x25, 0x25, 0x25, 0x25,
    0x25, 0x28, 0x2b, 0x2b, 0x2b, 0x2e, 0x2e, 0x03
};

#endif /* FX6_MENU_ITEMS_ASSIST_H */

/* ======================================================================
 * view_fill paint contract (appFw+0xc2750c), measured from image 658's fill=0
 * ======================================================================
 * A view_fill with only geometry draws nothing. onDrawNotice gates on three fields:
 *
 *   +0x1fc u8   enabled
 *   +0x200 s32  COLOUR ResID (namespace 6), -1 = none
 *   +0x208 u8   "have inline colour" flag, second chance when +0x200 == -1
 *
 *   enabled == 0                          -> mode 3, no paint
 *   +0x200 == -1 && +0x208 == 0           -> mode 3, no paint
 *   +0x200 != -1                          -> Sprite::setRectColorResID(slot, +0x200)   0xc275ec
 *   +0x200 == -1 && +0x208 != 0           -> inline colour bytes +0x205..+0x208         0xc27684
 *
 * Evidence: 0xc275ec tests +0x200 against -1 and calls PLT 0xb170f0 =
 * ux::gfxeng::Sprite::setRectColorResID(unsigned short, unsigned int). The alternative branch at
 * 0xc27684 reads +0x205/+0x206/+0x207/+0x208 and builds a stella::CColor. So +0x200 is a colour
 * resource id, not a string -- the descriptor field that feeds it is `desc+0x18`, and for
 * separator rows it really is a colour (e.g. `0x0200c00b`, `0x0200c00e`).
 *
 * Sprite slot used by both paths is `+0x210` inside the object (bound as `add x21,x19,#0x210`).
 */
/* Solid colour through the *inline* path (no resource lookup). */
static inline void fx6_fill_set_solid(void *fill, uint8_t r, uint8_t g, uint8_t b, uint8_t a)
{
    if (!fill) return;
    *(uint8_t  *)((char *)fill + 0x1fc) = 1;            /* enabled */
    *(uint32_t *)((char *)fill + 0x200) = 0xffffffffu;  /* no colour ResID */
    *(uint8_t  *)((char *)fill + 0x205) = r;
    *(uint8_t  *)((char *)fill + 0x206) = g;
    *(uint8_t  *)((char *)fill + 0x207) = b;
    *(uint8_t  *)((char *)fill + 0x208) = a;            /* doubles as "have colour" */
}

/* Colour through the resource path: this is what native panels and separators actually do. */
static inline void fx6_fill_set_color_resid(void *fill, uint32_t color_resid)
{
    if (!fill) return;
    *(uint8_t  *)((char *)fill + 0x1fc) = 1;
    *(uint32_t *)((char *)fill + 0x200) = color_resid;
}

/* Colour ids measured in color_cmn.uxc (namespace 6, marker 0x3a00, payload u32 RGBA). */
#define FX6_COLOR_BLACK     0x0200c001u   /* 000000ff */
#define FX6_COLOR_WHITE     0x0200c019u   /* ffffffff */
#define FX6_COLOR_SEPARATOR 0x0200c00eu   /* 777777ff */
#define FX6_COLOR_ACCENT    0x0200c011u   /* ee0000ff */
