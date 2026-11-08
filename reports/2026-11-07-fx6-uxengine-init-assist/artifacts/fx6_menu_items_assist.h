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

/* ---- class sizes charged by each creator, read from the creators themselves ----
 * Every creator adds its class size to the arena cursor (`ldr w0,[x19]; add w0,w0,#size;
 * str w0,[x19]`), so this table is authoritative and must drive any arena sizing:
 *
 *   idx 0 view_icon                      0x000668   (1.6 KiB)
 *   idx 1 view_fill                      0x000308   (0.8 KiB)
 *   idx 2 view_string                    0x001388   (4.9 KiB)
 *   idx 4 view_menu_item                 0x019788   (101.9 KiB)
 *   idx 5 view_frame                     0x001178   (4.4 KiB)
 *   idx 6 view_list_scroll_cursor_fixed  0x239870   (2278 KiB !)
 *
 * That last one is why run cp-bind-9e8b981f (image 659) ended with an empty gpe0: the descriptor
 * at index 1 of the setting table is `No4_SETTING_LIST_MAIN`, tag 0x42d5a20, class
 * view_list_scroll_cursor_fixed, and it cannot be placed in a small pool. Give it its own
 * >= 2.3 MiB allocation.
 */
static const uint32_t fx6_creator_size[8] = {
    0x000668u, 0x000308u, 0x001388u, 0x000000u,
    0x019788u, 0x001178u, 0x239870u, 0x000000u,
};
static inline uint32_t fx6_class_size(int idx)
{
    return (idx >= 0 && idx < 8) ? fx6_creator_size[idx] : 0;
}

/* Class tag (descriptor +0x00, appFw-relative) -> bytes to allocate before calling the ctor.
 * Use this instead of guessing a size: under-allocating a view_menu_item (0x19788) or a
 * view_list_scroll_cursor_fixed (0x239870) corrupts the heap and the failure surfaces later as
 * an unrelated crash inside libstella / libandromeda, or as
 *   "appfw-launch: malloc.c: sysmalloc: Assertion ... failed"
 * which is exactly what run cp-bind-1eb02dd3 (image 660) hit.
 *
 * Measured from the descriptors of the setting page:
 *   [00] 0x42d5860 touch      [01] 0x42d5a20 list 0x239870  [02..05] 0x42d57f0 string 0x1388
 *   [06..09] 0x42d58d0 item 0x19788
 * Instantiating the whole page costs 0x2a44b0 (2.6 MiB); skipping only [01] drops it to 0x6ac40. */
static inline uint32_t fx6_tag_instance_size(uint32_t tag_off)
{
    switch (tag_off) {
    case 0x42d57f0u: return 0x1388u;    /* view_string                     */
    case 0x42d5a50u: return 0x668u;     /* view_icon                       */
    case 0x42d5a40u: return 0x308u;     /* view_fill                       */
    case 0x42d58d0u: return 0x19788u;   /* view_menu_item                  */
    case 0x42d5a20u: return 0x239870u;  /* view_list_scroll_cursor_fixed   */
    default:         return 0u;         /* unknown: do NOT instantiate     */
    }
}

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

/* ---- view_frame internals, measured from 0xc27800 / 0xc27914 / 0xc27b20..0xc27be4 ----
 *
 * The five children are *inline sub-objects* at +0x228/+0x530/+0x838/+0xb40/+0xe48, and the ctor
 * also builds a five-entry pointer array at +0x1150..+0x1170 (terminated by self at +0x1170):
 *
 *   0xc278d8  str x25,[x19,#0x1150]   0xc278dc str x24,[x19,#0x1158]
 *   0xc278e0  str x23,[x19,#0x1160]   0xc278e4 str x22,[x19,#0x1168]
 *   0xc278c4  str x21,[x19,#0x1170]   <- x21 = this, used as the loop terminator
 *   0xc278e8  ldr x0,[x20],#8 ; bl setParent(x0, this)   ; until x20 == this+0x1178
 *
 * The per-edge setter 0xc27914(frame, slot, color, const int32_t rect4[4]) then does:
 *
 *   0xc27920  add  x21,x0,w1,sxtw #3       ; x21 = frame + slot*8
 *   0xc27934  ldr  x0,[x21,#0x1150]        ; child = children[slot]   (NOTE the +0x1150 base!)
 *   0xc2793c  ldr  x1,[x1,#0x140] ; blr x1 ; child->onCreate()
 *   0xc279a8  str  w22,[x0,#0x30]          ; child+0x30 = colour argument
 *   0xc279ac  ldrb w1,[x19,#0x220] ; strb w1,[x0,#0x34]   ; child+0x34 = frame+0x220
 *   0xc27984  stp  x2,x3,[x0]              ; rect[0],rect[1] -> child+0x00/+0x08
 *   0xc279a0  stp  x2,x3,[x0,#0x10]        ; rect[2],rect[3] -> child+0x10/+0x18
 *   0xc279b0  stp  x2,x3,[x0,#0x20]        ; caption ids + style
 *   0xc279c4  blr  child->onDraw()
 *
 * and 0xc27b20..0xc27be4 derives the four edge rects from the frame's own geometry — it reads
 * exactly these fields and nothing else:
 *
 *   0xc27b20  ldrh w1,[x19,#0x218]   ; e = border thickness (u16)
 *   0xc27b28  ldr  w0,[x19,#0x1f0]   ; w
 *   0xc27b60  ldr  w3,[x19,#0x1f4]   ; h
 *   0xc27b2c  mov  x3,x21            ; x21 = &rect4 on the stack, filled from the above
 *   0xc27b48  mov  w1,#1 ; bl 0xc27914
 *
 * Colour selection per edge (0xc27b30..0xc27be4): if the edge's own field at
 * +0x204/+0x208/+0x20c/+0x210 is != -1 that value is used, otherwise the edge falls back to
 * +0x200 (`0xc27bd0 ldr w2,[x19,#0x200]`). So a frame needs at least `+0x200 != -1`, exactly like
 * a plain view_fill needs its colour.
 *
 * Do NOT recompute the edge rects in your own code: the native body already does it from
 * +0x1e8/+0x1ec/+0x1f0/+0x1f4/+0x218, and the exact arithmetic there is style-dependent (+0x21c
 * selects among three shapes, anything else throws). Set the fields and call onDrawNotice. */
#define FX6_FRAME_CHILD_PTR_BASE 0x1150u

static inline void *fx6_frame_child_ptr(void *frame, int slot)
{
    if (!frame || slot < 0 || slot > 3) return 0;
    return *(void **)((char *)frame + FX6_FRAME_CHILD_PTR_BASE + (unsigned)slot * 8u);
}

/* Configure a frame the way the native pages do: geometry, border thickness, and the four edge
 * colours (colour ResIDs from color_cmn.uxc, or 0xffffffff for "fall back to +0x200").
 * `edge` is in pixels; native panels use small values such as 2 for a hairline. */
static inline void fx6_frame_setup(void *frame, int x, int y, int w, int h,
                                   uint16_t edge, uint32_t top_color, uint32_t bottom_color,
                                   uint32_t right_color, uint32_t left_color, uint32_t fill_color)
{
    if (!frame) return;
    *(int32_t  *)((char *)frame + 0x1e8) = x;
    *(int32_t  *)((char *)frame + 0x1ec) = y;
    *(int32_t  *)((char *)frame + 0x1f0) = w;
    *(int32_t  *)((char *)frame + 0x1f4) = h;
    *(uint16_t *)((char *)frame + 0x218) = edge;
    *(uint8_t  *)((char *)frame + 0x1fc) = 1;
    *(uint32_t *)((char *)frame + 0x200) = fill_color;
    *(uint32_t *)((char *)frame + 0x204) = top_color;
    *(uint32_t *)((char *)frame + 0x208) = bottom_color;
    *(uint32_t *)((char *)frame + 0x20c) = right_color;
    *(uint32_t *)((char *)frame + 0x210) = left_color;
    *(uint32_t *)((char *)frame + 0x21c) = 0;   /* style 0 = uniform border */
}

/* Drive a configured frame: onCreate (+0x148) then onDrawNotice (+0x158).
 * onDrawNotice itself fills the five child view_fill objects and calls their onCreate/onDraw,
 * so this single call is what puts four border edges plus the background into the framebuffer. */
static inline void fx6_frame_draw(void *frame)
{
    if (!frame) return;
    void **vt = *(void ***)frame;
    if (!vt) return;
    if (vt[0x148 / 8]) ((void (*)(void *))vt[0x148 / 8])(frame);
    if (vt[0x158 / 8]) ((void (*)(void *))vt[0x158 / 8])(frame);
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

/* Who calls Widget::setParent, measured (23 call sites in appFw):
 *
 *   view_fill 0xc27698      -> NO setParent at all. The ctor ends in `b 0xb17920`
 *                              (Sprite::Sprite()) on its +0x210 sub-object. Passing a NULL
 *                              `param` is fine; the `param` argument is only read at
 *                              [x20]/[x20+8]/[x20+0x20], so give it a zeroed 0x40 buffer.
 *   view_string 0xc3af98    -> tail-calls setParent at 0xc3b0c0 with x1 = the ctor's x1,
 *                              so its `param` argument must be a real widget.
 *   view_icon 0xc2c188      -> setParent at 0xc2c1f8 with x1 = x19 (itself) as the child and
 *                              x0 = x21, a *nested* widget at this+0x240. This is internal
 *                              wiring, not the caller's parent.
 *   view_menu_item 0xc341d4 -> two setParent calls (0xc3441c loop, 0xc34430) that attach the
 *                              ten internal children to `this`. Also internal.
 *
 * setParent dereferences its first argument immediately:
 *   libuxengine+0xa1fe8  ldr x0,[x1] ; ldr x1,[x0,#0x10] ; blr x1
 * so wherever a ctor forwards the caller's argument there, that argument must be a real widget.
 * For view_fill it is not required. */
#define FX6_PARENT_REQUIRED_FOR_VIEW_STRING 1

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

/* A view_menu_item never paints itself. onDrawNotice (0xc35358) puts its nine row children to
 * sleep, then dispatches on +0x200 to a style handler, and the handler forwards to the shared row
 * renderer appFw+0xc347b0, which drives the *child* widget:
 *
 *     0xc347d4  ldr x0,[x22,#0x730]     ; x22 = self + slot*8 + 0x19000
 *     0xc3493c  ldr x1,[x0] ; ldr x1,[x1,#0x148] ; blr x1   ; child onCreate
 *     0xc3494c  ldr x1,[x1,#0x158]                            ; child onDraw
 *
 * i.e. the paint target is   *(void**)((char*)item + 0x19730 + slot*8)
 * Those nine pointers are installed by the ctor (0xc341d4), which builds one 0xc208d0, four
 * view_icon, two view_string and several page classes.
 *
 * Consequence: ctor + setRect + setPaint + onDraw on a bare view_menu_item paints NOTHING. To get
 * pixels either drive the child returned by fx6_menu_item_child() directly, or make the whole
 * presenter state (style, slot, caption dictionary, child enable flags) coherent first.
 */
#define FX6_MENU_ITEM_CHILD_BASE 0x19730u

static inline void *fx6_menu_item_child(void *item, int slot)
{
    if (!item || slot < 0 || slot > 9) return 0;
    return *(void **)((char *)item + FX6_MENU_ITEM_CHILD_BASE + (unsigned)slot * 8u);
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

/* ======================================================================
 * One-call helpers for the dynamic line (665+), all built from measured facts
 * ======================================================================
 * Each helper takes the object already constructed by the native ctor and only writes the fields
 * that the corresponding onDrawNotice actually reads. No coordinate, label or colour is invented:
 * geometry and colours come from the descriptor table / color_cmn.uxc, and the caller passes them.
 */

/* view_frame: geometry + border thickness + per-edge colours, then draw.
 * `edge` in pixels (native separators are 2). Pass 0xffffffff for an edge to fall back to
 * `fill_color`. Style +0x21c stays 0 (uniform border). */
static inline void fx6_frame_render(void *frame, int x, int y, int w, int h, uint16_t edge,
                                    uint32_t fill_color,
                                    uint32_t top, uint32_t bottom, uint32_t right, uint32_t left)
{
    fx6_frame_setup(frame, x, y, w, h, edge, top, bottom, right, left, fill_color);
    fx6_frame_draw(frame);
}

/* view_icon: image ResID + geometry, then onCreate/onDrawNotice. */
static inline void fx6_icon_render(void *icon, int x, int y, int w, int h, uint32_t image_resid)
{
    if (!icon) return;
    fx6_icon_set_rect(icon, x, y, w, h);
    fx6_icon_set_image(icon, image_resid);
    fx6_widget_ondraw_generic(icon);
}

/* view_menu_item: style + slot geometry + caption/value ids, then onCreate/onDrawNotice.
 * Remember onDrawNotice drives the child at +0x19730+slot*8, so this only produces pixels once
 * that child itself is enabled (see fx6_menu_item_child). */
static inline void fx6_menu_item_render(void *item, int x, int y, int w, int h,
                                        uint32_t style, uint32_t caption_resid, uint32_t value_resid)
{
    if (!item) return;
    fx6_menu_item_set_rect(item, x, y, w, h);
    fx6_menu_item_set_style(item, style);
    fx6_menu_item_set_text_ids(item, caption_resid, value_resid);
    fx6_widget_ondraw_generic(item);
}

/* ======================================================================
 * view_icon image pipeline — where the decoded bitmap actually lands
 * ======================================================================
 * The icon widget owns a Sprite at `icon + 0x550` (ctor 0xc2c188 creates it there), and
 * onCreate 0xc2c044 fills that sprite's colour table:
 *
 *   0xc2c054  add  x22,x0,#0x550        ; sprite
 *   0xc2c068  bl   0xb19500             ; Widget::initSprite(sprite, 9)
 *   0xc2c0d0  mov  w0,#1 ; strb w0,[x19,#0x660]
 *   0xc2c0d8  ldrb w4,[x19,#0x21f]      ; RGBA bytes at +0x21c..+0x21f
 *   0xc2c0ec  bl   0xb18ce0             ; stella::CColor(r,g,b,a)
 *   0xc2c100  bl   0xb187b0             ; sprite->setRectColor(slot, colour), slots 0..8
 *
 * onDrawNotice 0xc2d100 then, when `+0x1fc != 0 && +0x20c != -1`:
 *
 *   0xc2d240  mov  w0,w21               ; w21 = image ResID (+0x20c)
 *   0xc2d24c  bl   0xb16eb0             ; ResourceManager::getImageOption(resid, NULL, 0)  -> count
 *   0xc2d258  bl   0xb18810             ; ResourceManager::sys_getInstance()
 *   0xc2d270  bl   0xb16eb0             ; getImageOption(resid, &portion, 2)               -> portion
 *   0xc2d278  ldrh w0,[x29,#0x50]       ; portion.count
 *   0xc2d288  ldrh w0,[x29,#0x52]       ; portion.patch flag
 *   0xc2d2a0  bl   0xb18c60             ; sprite->setPatchImageCache(flag)
 *   0xc2d334  bl   0xb17ac0             ; Sprite something on the 9-slot table
 *   0xc2d344  bl   0xc2c508 / 0xc2c368  ; geometry helpers
 *   0xc2d388  bl   0xb16ed0             ; Sprite::setRectSize / setClipSize family
 *   0xc2d3cc  bl   0xb19f50             ; Sprite::setImage / drawImage family
 *   0xc2d3d4  bl   0xc2d00c             ; the actual blit of the decoded bitmap
 *
 * So the bitmap is NOT stored at a fixed integer offset in the icon object: the icOn keeps a
 * Sprite at +0x550, and the decoded ImageData is handed to that sprite, which owns the pixel
 * buffer. The two fields that gate the whole path remain `+0x1fc` (enable) and `+0x20c`
 * (image ResID).
 */
#define FX6_ICON_SPRITE_OFF 0x550u

static inline void *fx6_icon_sprite(void *icon)
{
    return icon ? (void *)((char *)icon + FX6_ICON_SPRITE_OFF) : 0;
}

/* Full native icon blit: geometry + image ResID + colour/clip defaults, then onCreate and
 * onDrawNotice exactly as the native class does it. This is the icon analogue of
 * fx6_render_fill: it reaches the same two virtual slots the class itself uses. */
static inline void fx6_icon_blit(void *icon, int x, int y, int w, int h,
                                 uint32_t image_resid, uint8_t r, uint8_t g, uint8_t b, uint8_t a)
{
    if (!icon) return;
    *(int32_t  *)((char *)icon + 0x1e8) = x;
    *(int32_t  *)((char *)icon + 0x1ec) = y;
    *(int32_t  *)((char *)icon + 0x1f0) = w;
    *(int32_t  *)((char *)icon + 0x1f4) = h;
    *(uint8_t  *)((char *)icon + 0x1fc) = 1;          /* enable            */
    *(uint32_t *)((char *)icon + 0x20c) = image_resid; /* image ResID       */
    *(uint8_t  *)((char *)icon + 0x21c) = r;           /* clip colour RGBA  */
    *(uint8_t  *)((char *)icon + 0x21d) = g;
    *(uint8_t  *)((char *)icon + 0x21e) = b;
    *(uint8_t  *)((char *)icon + 0x21f) = a;
    *(uint16_t *)((char *)icon + 0x204) = (uint16_t)w; /* clip w            */
    *(uint16_t *)((char *)icon + 0x206) = (uint16_t)h; /* clip h            */
    void **vt = *(void ***)icon;
    if (!vt) return;
    if (vt[0x148 / 8]) ((void (*)(void *))vt[0x148 / 8])(icon);   /* onCreate     */
    if (vt[0x158 / 8]) ((void (*)(void *))vt[0x158 / 8])(icon);   /* onDrawNotice */
}

/* ======================================================================
 * 669 — Resolved Big-6 / menu caption ResIDs (all verified against the uxc index)
 * ======================================================================
 * Index key rule (this is the part that was wrong before): a packed ResID is resolved with
 *     ns  = (id >> 13) & 0x7ff
 *     key = (ns << 13) | (id & 0x1fff)          <-- NOT 0x4000 + idx
 * and then looked up in string_english.uxc (ns 1) or string_english_2.uxc (ns 2).
 *
 * Verified: 0x02002227 -> key 0x2227 -> "Shooting"; 0x02005082 -> key 0x5082 -> "FPS".
 */
static inline int fx6_resid_ns(uint32_t id)   { return (int)((id >> 13) & 0x7ffu); }
static inline int fx6_resid_index(uint32_t id) { return (int)(id & 0x1fffu); }
static inline uint32_t fx6_resid_key(uint32_t id)
{
    return (uint32_t)((fx6_resid_ns(id) << 13) | fx6_resid_index(id));
}

/* The A84 caption/format table at appFw+0x23be620 (84 packed ResIDs, 21 of them ns=2).
 * Entry [i] pairs a *label* (ns 1 or 2) with the neighbouring entry, which is usually a
 * `${v1}`/`${v2}` format template. Measured contents of the first entries:
 *
 *   [00] 0x020043ed 'Frequency'      [01] 0x02005082 'FPS'
 *   [02] 0x02004575 'Frame Rate'     [04] 0x02004d96 'Shutter Angle'
 *   [06] 0x02004d94 'Shutter Speed'  [08] 0x02004d98 'ECS Frequency'
 *   [12] 0x020030cc 'Angle (Step)'   [14] 0x020030ce 'Angle (Continuous)'
 *   [16] 0x020030d1 'Speed (Step)'   [18] 0x020030dc 'Speed (Continuous)'
 *   [20] 0x020020a2 'Speed: \ue5db${v1}'       [28] 0x020020ae 'Angle: ${v1}.${v2:02}'
 *   [43] 0x02003003 'Look'           [58] 0x02002464 'S-Cinetone'
 *   [60] 0x02002466 'Standard'       [64] 0x020023ed 'ITU709'
 *   [68] 0x020023f1 'HLG Live'       [72] 0x020023f5 'HLG Natural'
 *   [74] 0x02002830 'LUT On'         [76] 0x020028ee 'LUT Off'
 */
#define FX6_A84_TABLE_ADDR 0x23be620u
#define FX6_A84_TABLE_COUNT 84u

/* The Big-6 style labels, resolved by value so a probe never has to guess: */
#define FX6_TXT_FPS          0x02005082u   /* ns2 'FPS'            */
#define FX6_TXT_SHUTTER      0x020050e8u   /* ns2 'Shutter'        */
#define FX6_TXT_SHUTTER_N1   0x02002fe1u   /* ns1 'Shutter'        */
#define FX6_TXT_ISO          0x02004c32u   /* ns2 'ISO'            */
#define FX6_TXT_GAIN         0x0200420eu   /* ns2 'Gain'           */
#define FX6_TXT_ND_FILTER    0x02004288u   /* ns2 'ND Filter'      */
#define FX6_TXT_WHITE_BAL    0x02005689u   /* ns2 'White Balance'  */
#define FX6_TXT_WHITE_BAL_N1 0x02002a67u   /* ns1 'White Balance'  */
#define FX6_TXT_BASE_LOOK    0x020023f8u   /* ns1 'Base Look'      */
#define FX6_TXT_CODEC        0x02004261u   /* ns2 'Codec'          */
#define FX6_TXT_COLOR_MODE   0x020044f5u   /* ns2 'Color Mode'     */
#define FX6_TXT_VF_COLOR_MODE 0x020044f7u  /* ns2 'VF Color Mode'  */
#define FX6_TXT_ISO_GAIN     0x02005459u   /* ns2 'ISO/Gain'       */
#define FX6_TXT_FREQUENCY    0x020043edu   /* ns2 'Frequency'      */
#define FX6_TXT_FRAME_RATE   0x02004575u   /* ns2 'Frame Rate'     */
#define FX6_TXT_SHUTTER_ANGLE 0x02004d96u  /* ns2 'Shutter Angle'  */
#define FX6_TXT_SHUTTER_SPEED 0x02004d94u  /* ns2 'Shutter Speed'  */
#define FX6_TXT_OFF          0x02005292u   /* ns2 'Off'            */
#define FX6_TXT_AUTO_N2      0x020056e7u   /* ns2 'Auto'           */
#define FX6_TXT_MANUAL_N2    0x020056ecu   /* ns2 'Manual'         */

/* Per-widget param_t initialisers that carry a (caption, caption, -1, -1) tuple.
 * These are what the presenter feeds the six big cells from: no descriptor +0x18 in the
 * 0x48-stride tables carries a Big-6 title except No27_THUMBNAIL_PROPERTIES_FPS_TITLE. */
#define FX6_PARAM_GAIN        0x2da5a20u   /* +0x18: 0x0200420e 'Gain', 0x020043b3 'Gain' */
#define FX6_PARAM_ND_FILTER   0x2dd2c00u   /* +0x18: 0x020054fd 'ND Filter' x2            */
#define FX6_PARAM_COLOR_MODE  0x2dd8180u   /* +0x00: 0x020044f5/44f6 'Color Mode',
                                            *        0x020044f7 'VF Color Mode'        */

/* ======================================================================
 * 670 — Level-1 category titles: the (ResID, slot) pair list at appFw+0x226a6c0
 * ======================================================================
 * This is the table the presenters index instead of holding a plain ResID array. Each entry is
 *
 *      struct { uint32_t resid; uint32_t slot; }        stride 8
 *
 * and `slot` is what the presenter writes into a row widget's caption slot, with the widget then
 * looking the string up by `resid`. Slot numbers are denses and jump around, so *slot is NOT the
 * entry index* — e.g. the five FX6 section titles live at slots 0x234..0x237, not at 0..4.
 *
 * Measured, with the string rendered from string_english.uxc / string_english_2.uxc:
 *
 *   slot 0x234  0x02002227  'Shooting'
 *   slot 0x235  0x02002228  'Project'
 *   slot 0x236  0x02002229  'Monitoring'
 *   slot 0x237  0x0200222a  'Technical'
 *   slot 0x4ec  0x0200222b  'TC/Media'
 *   slot 0x2a4  0x020041fb  'Audio'        (ns2)
 *   slot 0x2a7  0x02004203  'Maintenance'  (ns2)
 *   slot 0x2a9  0x02004208  'User'         (ns2)
 *   slot 0x2aa  0x02004209  'Thumbnail'    (ns2)
 *   slot 0x233  0x02002223  'VF Adjust'
 *   slot 0x232  0x020029f8  'Look'
 *   slot 0x23c  0x0200225c  'Cine EI Setting'
 *   slot 0x23d  0x02002266  'Base ISO'
 *   slot 0x23e  0x02002296  'MLUT'
 *   slot 0x246  0x020023da  'Set'
 *   slot 0x247  0x020023f8  'Base Look'
 *   slot 0x248  0x020023fa  'Reset Paint Settings'
 *
 * The same table also carries the *paint/look* family and the AF family, which is why a naive
 * "search for a run of category ids" fails: the ids are not contiguous, the slots are.
 */
#define FX6_PAIRLIST_ADDR   0x226a6c0u
#define FX6_PAIRLIST_STRIDE 8u

#define FX6_SLOT_SHOOTING      0x234u
#define FX6_SLOT_PROJECT       0x235u
#define FX6_SLOT_MONITORING    0x236u
#define FX6_SLOT_TECHNICAL     0x237u
#define FX6_SLOT_TC_MEDIA      0x4ecu
#define FX6_SLOT_AUDIO_N2      0x2a4u
#define FX6_SLOT_MAINTENANCE   0x2a7u
#define FX6_SLOT_USER          0x2a9u
#define FX6_SLOT_THUMBNAIL     0x2aau
#define FX6_SLOT_VF_ADJUST     0x233u
#define FX6_SLOT_LOOK          0x232u
#define FX6_SLOT_CINE_EI       0x23cu
#define FX6_SLOT_BASE_ISO      0x23du
#define FX6_SLOT_MLUT          0x23eu
#define FX6_SLOT_SET           0x246u
#define FX6_SLOT_BASE_LOOK     0x247u
#define FX6_SLOT_RESET_PAINT   0x248u

/* Level-1 section titles as plain ResIDs, for probes that address widgets directly. */
#define FX6_TXT_SHOOTING   0x02002227u
#define FX6_TXT_PROJECT    0x02002228u
#define FX6_TXT_MONITORING 0x02002229u
#define FX6_TXT_TECHNICAL  0x0200222au
#define FX6_TXT_TC_MEDIA   0x0200222bu
#define FX6_TXT_AUDIO      0x0200211bu   /* ns1 'Audio' (0x2121 is 'NCM/Streaming' -- do not swap) */
#define FX6_TXT_AUDIO_N1   0x0200211bu   /* ns1 'Audio'          */
#define FX6_TXT_CAMERA     0x0200211au   /* ns1 'Camera'         */
#define FX6_TXT_PAINT_N2   0x020041fau   /* ns2 'Paint'          */
#define FX6_TXT_MAINTENANCE 0x02004203u  /* ns2 'Maintenance'    */
#define FX6_TXT_USER       0x02004208u   /* ns2 'User'           */
#define FX6_TXT_THUMBNAIL  0x02004209u   /* ns2 'Thumbnail'      */
#define FX6_TXT_NETWORK    0x0200420au   /* ns2 'Network'        */
#define FX6_TXT_PROJECT_N2 0x0200420bu   /* ns2 'Project'        */
#define FX6_TXT_TC_MEDIA_N2 0x0200420cu  /* ns2 'TC/Media'       */
#define FX6_TXT_TECHNICAL_N2 0x0200420du /* ns2 'Technical'      */
#define FX6_TXT_RECORDING  0x02004200u   /* ns2 'Recording'      */
#define FX6_TXT_MEDIA_N2   0x02004201u   /* ns2 'Media'          */
#define FX6_TXT_FILE       0x02004202u   /* ns2 'File'           */
#define FX6_TXT_SYSTEM     0x02004204u   /* ns2 'System'         */
#define FX6_TXT_OPERATION  0x02004207u   /* ns2 'Operation'      */

/* ======================================================================
 * 670 — Big-6 home central status area: TABLE 0x2e9e210 entries 0..36
 * ======================================================================
 * These descriptors already carry a live ResID in `desc+0x18`, so the static text renders with no
 * presenter involvement at all. All values below were re-resolved against the string containers:
 *
 *   0x02002f1d -> 'FF'        0x02005261 -> 'XAVC-I'    0x020051e7 -> 'Stop'
 *   0x02002959 -> '---<glyph>' 0x02002999 -> '3840P'    0x02005078 -> 'Rec'
 *   0x02002a48 -> 'Shot'      0x020029f0 -> 'Reel'
 *   0x0200284d -> glyph       0x02002956 -> glyph       0x02002822 -> glyph
 */
#define FX6_HOME_TABLE_ADDR 0x2e9e210u

#define FX6_STATUS_IMAGER_SCAN_MODE   0x02002f1du   /* 'FF'        [06] (336,257,208,32) */
#define FX6_STATUS_CODEC_NAME         0x02005261u   /* 'XAVC-I'    [07] (336,297,180,32) */
#define FX6_STATUS_MEDIA_PROXY_STOP   0x020051e7u   /* 'Stop'      [15] (672,342,88,32)  */
#define FX6_STATUS_MEDIA_REMAIN_TIME  0x02002959u   /* '---<glyph>'[16] (672,342,88,32)  */
#define FX6_STATUS_RESOLUTION         0x02002999u   /* '3840P'     [18] (520,297,84,32)  */
#define FX6_STATUS_RECSTATE           0x02005078u   /* 'Rec'       [22] (212,278,82,32)  */
#define FX6_STATUS_MEDIA_SLOT_B_ICON  0x02002956u   /* glyph       [31] (602,341,70,34)  */
#define FX6_STATUS_MEDIA_SLOT_A_ICON  0x02002822u   /* glyph       [32] (420,341,70,34)  */
#define FX6_STATUS_SHOT_ITEM_NAME     0x02002a48u   /* 'Shot'      [34] (611,297,70,32)  */
#define FX6_STATUS_REEL_ITEM_NAME     0x020029f0u   /* 'Reel'      [35] (611,257,70,32)  */

/* The only descriptors whose caption slot is still -1: a probe must supply these itself. */
#define FX6_STATUS_IS_RUNTIME_FILLED(id) ((id) == 0xffffffffu)
#define FX6_STATUS_RUNTIME_SLOTS 6   /* No1071/No2071 TC value, No1172/No2172 clip number,
                                      * No2141 bitrate, No1162 camreel/title value          */

/* Panel colours used by the status area (namespace 6, from color_cmn.uxc). */
#define FX6_COLOR_BG_PANEL   0x0200c001u   /* opaque black  */
#define FX6_COLOR_BG_INNER   0x0200c008u   /* inner panel   */
#define FX6_COLOR_SEP_STATUS 0x0200c00eu   /* 0x777777 separator */

/* ======================================================================
 * 671 — The slot -> ResID lookup is a runtime unordered_map, not a table scan
 * ======================================================================
 * Two pair lists are consumed once at init by appFw+0xb1a868:
 *
 *   mapA (text): 0x226a6c0 .. 0x2272a80   (0x83c0 bytes = 4216 entries)
 *   mapB (icon): 0x2272a80 .. 0x2272f18   (0x498  bytes =  147 entries)
 *
 * both handed to appFw+0xc15c44 (unordered_map range ctor: __floatunditf, _M_next_bkt,
 * _M_need_rehash, operator new), stored in .bss at 0x303e738 (mapA) and 0x303e6c8 (mapB),
 * and registered with __cxa_atexit.
 *
 * The resolver is appFw+0xc18548(menu_item_id_t) -> ResID:
 *
 *     if (id == 0x02004c47 || id == -1) return 0;
 *     node = mapA.find(id); if (node) return node->value;
 *     node = mapB.find(id); if (node) return node->value;
 *     return 0xd00;                        <- unknown id
 *
 * So a probe cannot read the mapping from .rodata without reimplementing the hash; either call the
 * resolver through the appFw base pointer, or read the two source arrays directly (they are plain
 * (resid, slot) pairs, which is what FX6_PAIRLIST_ADDR describes).
 */
#define FX6_LOOKUP_FN_OFFSET   0xc18548u   /* appFw + this -> ResID, 35 call sites */
#define FX6_LOOKUP_SENTINEL    0x02004c47u
#define FX6_LOOKUP_UNKNOWN     0xd00u

#define FX6_MAPA_BEGIN  0x226a6c0u         /* slot -> text ResID (ns 1/2), 4216 pairs */
#define FX6_MAPA_END    0x2272a80u
#define FX6_MAPB_BEGIN  0x2272a80u         /* slot -> icon ResID (ns 0),  147 pairs */
#define FX6_MAPB_END    0x2272f18u

#define FX6_MAPA_BSS    0x303e738u
#define FX6_MAPB_BSS    0x303e6c8u

/* The 35 call sites of the resolver, in address order — the entry points of the text system. */
#define FX6_LOOKUP_CALLERS \
    0xc187d8u, 0xc18854u, 0xc264d8u, 0xc55990u, 0xc5599cu, 0xf64648u, 0xf646acu, 0xf669a0u, \
    0xf66a04u, 0xf6c13cu, 0xf6c1a0u, 0xf7731cu, 0xf77730u, 0xfb9a98u, 0xfb9e6cu, 0xfb9fa4u, \
    0xfba018u, 0xfbe448u, 0xfd0870u, 0xfdac48u, 0xfdc374u, 0xfe0510u, 0xfe4884u, 0xfe7e74u, \
    0xfec610u, 0xfec920u, 0xfeca18u, 0xfecbccu, 0xfeccbcu, 0xfef8f4u, 0xff1a28u, 0xff3858u, \
    0xff57c8u, 0xff7904u, 0xffb830u

/* ----------------------------------------------------------------------
 * Page-break marker: class tag 0x42d5a60 with an all-zero rect separates pages inside one table.
 * `0x2ea3e50` is NOT "28 setting entries": rows 0..9 are the Setting main page, `[10]` is a break,
 * then the text-dialog / transferring / toast pages follow.
 * ---------------------------------------------------------------------- */
#define FX6_TAG_PAGE_BREAK 0x42d5a60u
#define FX6_IS_PAGE_BREAK(tag, rect) \
    (((tag) == FX6_TAG_PAGE_BREAK) && ((rect)[0] == 0 && (rect)[1] == 0 && \
     (rect)[2] == 0 && (rect)[3] == 0))

#define FX6_SETTING_MAIN_FIRST 0u           /* 0x2ea3e50 rows 0..9  */
#define FX6_SETTING_MAIN_LAST  9u
#define FX6_THREELAYER_MAIN_FIRST 0u        /* 0x2ea02f8 rows 0..34 */
#define FX6_THREELAYER_ROWS_FIRST 10u       /* seven second-layer rows: 10..16 */
#define FX6_THREELAYER_ROWS_LAST  16u
#define FX6_THREELAYER_BUTTONS_FIRST 2u     /* eight navigation buttons: 2..9 */
#define FX6_THREELAYER_BUTTONS_LAST  9u

/* ----------------------------------------------------------------------
 * Format templates that actually exist for the runtime-filled value slots.
 * ---------------------------------------------------------------------- */
#define FX6_FMT_BITRATE_MBPS 0x02002be2u    /* '${v1}.${v2} Mbps (${v3} %)'  -> No2141_BITRATE */
#define FX6_FMT_MBPS_UNIT    0x02002b74u    /* 'Mbps' */
#define FX6_FMT_TC_GLYPHS_A  0x0200220cu    /* '${v1:02}\ue5d5${v2:02}\ue5d8' */
#define FX6_FMT_TC_GLYPHS_B  0x0200220du    /* '${v1:02}\ue5d8${v2:02}\ue5d7' */
/* There is NO 'HH:MM:SS:FF' template in either string container. The TC widgets
 * (No1071_/No2071_TIME_CODE_VALUE) and the clip-number / camreel value slots have no format
 * resource; a probe must write an already-composed string or leave them at -1 (undrawn). */
#define FX6_HAS_TIMECODE_TEMPLATE 0

/* Icon families for the category slots, from mapB (all verified in image_00_169.uxc): */
#define FX6_ICON_SLOT_BACK     0x02000154u  /* No2_Backiconinthesecondlayer (378,112,38,38) */
#define FX6_ICON_SLOT_BACK_ALT 0x02000152u
#define FX6_ICON_SLOT_BACK_ALT2 0x02000153u

/* ======================================================================
 * 672 — THE STANDARD 0x48 view_string DESCRIPTOR TEMPLATE
 * ======================================================================
 * Why 12 synthesised view_strings produced no glyphs while 24 native ones did:
 *
 *   The native descriptors are consumed by the FACTORY at appFw+0xc1935c, and its view_string
 *   branch (0xc19594..0xc195d0) copies six fields into the object:
 *
 *       0xc19594  ldr w1,[x19,#0x18] ; str w1,[x0,#0x30]     ; desc+0x18 -> obj+0x200 text ResID
 *       0xc195c0  stp w4,w3,[x0,#0x38]                      ; desc+0x24 -> +0x208, +0x28 -> +0x20c
 *       0xc195c4  stp w1,w5,[x0,#0x40]                      ; desc+0x1c -> +0x210, +0x20 -> +0x214
 *       0xc195c8  str wzr,[x0,#0x48]                        ; +0x218 = 0
 *       0xc195cc  ldr w1,[x19,#0x2c] ; str w1,[x0,#0x844]   ; desc+0x2c -> +0xa14
 *
 *   (`x0` is the vt[0x140] sub-object = obj+0x1d0, so +0x30 there is obj+0x200, etc.)
 *
 *   A synthetic widget built by calling the constructor 0xc3af98 directly never gets those six
 *   writes, so +0x208/+0x20c/+0x210/+0x214/+0xa14 stay 0. The ctor itself only sets
 *   +0x200 = -1 and +0xa14 = 0x44 (0xc3b078 / 0xc3b080); everything else comes from the factory.
 *   With +0x200 = -1 and +0x610 = 0, onDrawNotice takes the early exit at 0xc3bc14..0xc3bc1c and
 *   never reaches the text path at 0xc3c2b4 — that is exactly "no TextSprite glyph".
 *
 * Byte-for-byte template taken from three descriptors that DO render
 * (TABLE 0x2e9e210 entries 6, 7, 18):
 *
 *   +0x00  0x042d57f0   class tag (view_string)                 REQUIRED
 *   +0x04  0x00000000                                          -
 *   +0x08  <ptr>        debug/name pointer (any valid C string)  recommended
 *   +0x0c  0x00000000                                          -
 *   +0x10  0x00000000                                          -
 *   +0x14  0x00000000                                          -
 *   +0x18  <ResID>      text ResID  -> obj+0x200                REQUIRED
 *   +0x1c  0x0200a029   layout id   -> obj+0x210                 REQUIRED
 *   +0x20  0x00000001   style id    -> obj+0x214                 REQUIRED (always exactly 1)
 *   +0x24  0x0200600f   FontName    -> obj+0x208                 REQUIRED
 *   +0x28  0x0200600e   FontName    -> obj+0x20c                 REQUIRED
 *   +0x2c  0x00000044   -> obj+0xa14 (68; every 0x2e9e210 string uses 0x44)  REQUIRED
 *   +0x30  0x00000ce2   flags                                    keep 0xce2
 *   +0x34  0x00002ce9   flags                                    keep 0x2ce9
 *   +0x38  0x<idx><<16> widget id (descriptor index << 16)        recommended
 *   +0x3c  x | y<<16    rect origin (u16 pair)                   REQUIRED
 *   +0x40  w | h<<16    rect size   (u16 pair)                   REQUIRED
 *   +0x44  0x00000000   reserved                                 keep 0
 *
 * Field statistics over all 56 view_string descriptors of TABLE 0x2e9e210 (measured, not guessed):
 *
 *   +0x1c: 0x0200a029 x47, 0x0200a02b x7, 0x0200a02a x2
 *   +0x20: 0x00000001 x56                      <- never anything else
 *   +0x24: 0x02006008 x24, 0x0200600f x20, 0x0200600d x5, 0x0200600a x3
 *   +0x28: 0x0200600e x44, 0x02006002 x6, 0x0200601b x6
 *   +0x2c: 0x00000044 x56
 *   +0x30: 0x00000ce2 x56
 *   +0x34: 0x00002ce9 x56
 *   +0x44: 0x00000000 x56
 *   +0x38: 0x<index><<16> x56  (matches the descriptor's own row index)
 */
#define FX6_DESC_STRIDE        0x48u
#define FX6_DESC_TAG_VS        0x042d57f0u   /* view_string                    */
#define FX6_DESC_TAG_VF        0x042d5a40u   /* view_fill                      */
#define FX6_DESC_TAG_VI        0x042d5a50u   /* view_icon                      */
#define FX6_DESC_TAG_MI        0x042d58d0u   /* view_menu_item                 */
#define FX6_DESC_TAG_LIST      0x042d5a20u   /* view_list_scroll_cursor_fixed  */
#define FX6_DESC_TAG_TOUCH     0x042d5860u   /* full-screen touch              */
#define FX6_DESC_TAG_PAGEBREAK 0x42d5a60u    /* page separator, all-zero rect  */

#define FX6_DESC_OFF_TAG       0x00u
#define FX6_DESC_OFF_NAME      0x08u
#define FX6_DESC_OFF_TEXT      0x18u
#define FX6_DESC_OFF_LAYOUT    0x1cu
#define FX6_DESC_OFF_STYLE     0x20u
#define FX6_DESC_OFF_FONT_A    0x24u
#define FX6_DESC_OFF_FONT_B    0x28u
#define FX6_DESC_OFF_FONTSIZE  0x2cu
#define FX6_DESC_OFF_FLAG_A    0x30u
#define FX6_DESC_OFF_FLAG_B    0x34u
#define FX6_DESC_OFF_WIDGET_ID 0x38u
#define FX6_DESC_OFF_RECT_XY   0x3cu
#define FX6_DESC_OFF_RECT_WH   0x40u
#define FX6_DESC_OFF_RESERVED  0x44u

/* The exact constants the working rows use. */
#define FX6_VS_LAYOUT_DEFAULT  0x0200a029u
#define FX6_VS_LAYOUT_ALT_A    0x0200a02au
#define FX6_VS_LAYOUT_ALT_B    0x0200a02bu
#define FX6_VS_STYLE           0x00000001u
#define FX6_VS_FONT_06008      0x02006008u
#define FX6_VS_FONT_0600f      0x0200600fu
#define FX6_VS_FONT_0600d      0x0200600du
#define FX6_VS_FONT_0600a      0x0200600au
#define FX6_VS_FONT2_0600e     0x0200600eu
#define FX6_VS_FONT2_06002     0x02006002u
#define FX6_VS_FONT2_0601b     0x0200601bu
#define FX6_VS_FONTSIZE        0x00000044u
#define FX6_VS_FLAG_A          0x00000ce2u
#define FX6_VS_FLAG_B          0x00002ce9u

typedef struct __attribute__((packed)) {
    uint32_t tag;           /* +0x00 */
    uint32_t zero04;        /* +0x04 */
    uint32_t name;          /* +0x08  debug-name pointer (appFw-relative u32) */
    uint32_t zero0c;        /* +0x0c */
    uint32_t zero10;        /* +0x10 */
    uint32_t zero14;        /* +0x14 */
    uint32_t text_resid;    /* +0x18 -> obj+0x200   */
    uint32_t layout;        /* +0x1c -> obj+0x210   */
    uint32_t style;         /* +0x20 -> obj+0x214   */
    uint32_t font_a;        /* +0x24 -> obj+0x208   */
    uint32_t font_b;        /* +0x28 -> obj+0x20c   */
    uint32_t font_size;     /* +0x2c -> obj+0xa14   */
    uint32_t flag_a;        /* +0x30                */
    uint32_t flag_b;        /* +0x34                */
    uint32_t widget_id;     /* +0x38 = index << 16  */
    uint32_t rect_xy;       /* +0x3c = x | y<<16    */
    uint32_t rect_wh;       /* +0x40 = w | h<<16    */
    uint32_t reserved;      /* +0x44 = 0            */
} __attribute__((packed)) fx6_desc_view_string;   /* sizeof == 0x48 */

/* Fill a template that is guaranteed to satisfy every field the factory and onDrawNotice read.
 * `index` becomes the widget id; x/y/w/h are pixels. */
static inline void fx6_desc_view_string_init(fx6_desc_view_string *d, uint32_t index,
                                             uint32_t text_resid, int x, int y, int w, int h)
{
    d->tag        = FX6_DESC_TAG_VS;
    d->zero04     = 0;
    d->name       = 0;
    d->zero0c     = 0;
    d->zero10     = 0;
    d->zero14     = 0;
    d->text_resid = text_resid;
    d->layout     = FX6_VS_LAYOUT_DEFAULT;
    d->style      = FX6_VS_STYLE;
    d->font_a     = FX6_VS_FONT_0600f;
    d->font_b     = FX6_VS_FONT2_0600e;
    d->font_size  = FX6_VS_FONTSIZE;
    d->flag_a     = FX6_VS_FLAG_A;
    d->flag_b     = FX6_VS_FLAG_B;
    d->widget_id  = (index & 0xffffu) << 16;
    d->rect_xy    = ((uint32_t)(uint16_t)x) | ((uint32_t)(uint16_t)y << 16);
    d->rect_wh    = ((uint32_t)(uint16_t)w) | ((uint32_t)(uint16_t)h << 16);
    d->reserved   = 0;
}

/* If the widget already exists, the minimum correct post-conditions are these five writes —
 * they are what the factory does and what the synthetic path was missing. */
static inline void fx6_view_string_apply_desc(void *vs, const fx6_desc_view_string *d)
{
    if (!vs || !d) return;
    *(uint32_t *)((char *)vs + 0x200) = d->text_resid;
    *(uint32_t *)((char *)vs + 0x208) = d->font_a;
    *(uint32_t *)((char *)vs + 0x20c) = d->font_b;
    *(uint32_t *)((char *)vs + 0x210) = d->layout;
    *(uint32_t *)((char *)vs + 0x214) = d->style;
    *(uint32_t *)((char *)vs + 0xa14) = d->font_size;
    *(uint8_t  *)((char *)vs + 0x1fc) = 1;
}

/* ======================================================================
 * PHASE 8 — CORRECTED SEMANTICS OF mapA / mapB AND THE SLOT VOCABULARY
 * ======================================================================
 * The round-671 description of these maps as "slot -> ResID" was BACKWARDS. Measured:
 *
 *   mapA 0x226a6c0..0x2272a80, 4216 pairs, every FIRST element is a packed ResID
 *   (bits 31..24 == 0x02) and every SECOND element is a small slot id.
 *
 *         pair = { uint32_t resid; uint32_t slot; }
 *
 *   so mapA is  resid -> slot,  and the resolver appFw+0xc18548(resid) returns the SLOT,
 *   not a text id. Verified on the categories:
 *
 *         0x02002227 'Shooting'   -> slot 0x234
 *         0x02002228 'Project'    -> slot 0x235
 *         0x0200222b 'TC/Media'   -> slot 0x4ec
 *         0x020041fb 'Audio'(ns2) -> slot 0x2a4
 *         0x02004208 'User' (ns2) -> slot 0x2a9
 *
 *   2942 distinct slots; 1071 slots have several ResID aliases (locale / state variants),
 *   e.g. slot 0x016 has 7 aliases, slot 0x378 has 7.
 *
 *   mapB 0x2272a80..0x2272f18, 147 pairs, same layout but the ResID is a namespace-0 icon.
 *
 * Why the 35 call sites show no static slot arrays: they pass *ResIDs* (usually loaded from a
 * widget field such as [+0x30] or a computed register) and use the returned slot for indexing.
 * Only three sites pass a literal (all 512 = 0x200). So the per-category item lists are not
 * stored as slot arrays in .text; the mapping direction is ResID-first throughout.
 */

/* Resolved slot ids for the widgets a probe is most likely to need. */
/* ---- Phase 8: menu slot ids and their canonical text (from mapA at 0x226a6c0) ---- */
#define FX6_SLOTID_FOCUS_HOLD_BUTTON 0x001u   /* 0x02002006 'Focus Hold Button' */
#define FX6_SLOTID_FIXED 0x002u   /* 0x02002071 'Fixed' */
#define FX6_SLOTID_HIGH 0x003u   /* 0x020020cd 'High' */
#define FX6_SLOTID_LOW 0x004u   /* 0x020020ce 'Low' */
#define FX6_SLOTID_WHITE_BALANCE 0x005u   /* 0x020020d0 'White Balance' */
#define FX6_SLOTID_WIRELESS 0x006u   /* 0x020020fb 'Wireless' */
#define FX6_SLOTID_MULTI_FUNCTION_DIAL 0x007u   /* 0x0200210a 'Multi Function Dial' */
#define FX6_SLOTID_GRIP_DIAL 0x008u   /* 0x0200210b 'Grip Dial' */
#define FX6_SLOTID_HANDLE_DIAL 0x009u   /* 0x0200210c 'Handle Dial' */
#define FX6_SLOTID_CAMERA 0x00au   /* 0x0200211a 'Camera' */
#define FX6_SLOTID_AUDIO 0x00bu   /* 0x0200211b 'Audio' */
#define FX6_SLOTID_PROJECT 0x00cu   /* 0x0200211c 'Project' */
#define FX6_SLOTID_MONITORING 0x00du   /* 0x0200211d 'Monitoring' */
#define FX6_SLOTID_ASSIGNABLE_BUTTON 0x00eu   /* 0x0200211e 'Assignable Button' */
#define FX6_SLOTID_BATTERY 0x00fu   /* 0x0200211f 'Battery' */
#define FX6_SLOTID_MEDIA 0x010u   /* 0x02002120 'Media' */
#define FX6_SLOTID_NETWORK 0x011u   /* 0x02002122 'Network' */
#define FX6_SLOTID_FILE_TRANSFER 0x012u   /* 0x02002123 'File Transfer' */
#define FX6_SLOTID_SHOOTING_MODE 0x013u   /* 0x0200218a 'Shooting Mode' */
#define FX6_SLOTID_HEADPHONE_OUT 0x015u   /* 0x02002191 'Headphone Out' */
#define FX6_SLOTID_VOLUME 0x016u   /* 0x02002192 'Volume' */
#define FX6_SLOTID_GAMMA_DISP_ASSIST 0x017u   /* 0x0200219c 'Gamma Disp. Assist' */
#define FX6_SLOTID_VIDEO_FORMAT 0x018u   /* 0x020021b5 'Video Format' */
#define FX6_SLOTID_SIGNAL 0x019u   /* 0x020021b6 'Signal' */
#define FX6_SLOTID_MANUAL 0x01au   /* 0x020021d1 'Manual' */
#define FX6_SLOTID_AUTO 0x01bu   /* 0x020021d2 'Auto' */
#define FX6_SLOTID_LINKED_WITH_GAIN 0x01cu   /* 0x02002202 'Linked with gain' */
#define FX6_SLOTID_FORMAT 0x01du   /* 0x0200220f 'Format' */
#define FX6_SLOTID_AUTO_UPLOAD 0x01eu   /* 0x02002213 'Auto Upload' */
#define FX6_SLOTID_NO_DEVICE 0x01fu   /* 0x020029d0 'No Device' */
#define FX6_SLOTID_TETHERING 0x020u   /* 0x02002937 'Tethering' */
#define FX6_SLOTID_FOCUS_HOLD_BUTTON_ALT 0x021u   /* 0x02002225 'Focus Hold Button' */
#define FX6_SLOTID_ZONE 0x022u   /* 0x02002230 'Zone' */
#define FX6_SLOTID_FOCUS_SETTING 0x023u   /* 0x0200223e 'Focus Setting' */
#define FX6_SLOTID_CLIP_NAME_FORMAT 0x024u   /* 0x02002244 'Clip Name Format' */
#define FX6_SLOTID_FOCAL_LENGTH 0x025u   /* 0x0200224e 'Focal Length' */
#define FX6_SLOTID_INTERNAL_REC 0x026u   /* 0x0200225e 'Internal Rec' */
#define FX6_SLOTID_LOOK 0x232u   /* 0x020029f8 'Look' */
#define FX6_SLOTID_VF_ADJUST 0x233u   /* 0x02002223 'VF Adjust' */
#define FX6_SLOTID_SHOOTING 0x234u   /* 0x02002227 'Shooting' */
#define FX6_SLOTID_PROJECT_CAT 0x235u   /* 0x02002228 'Project' */
#define FX6_SLOTID_MONITORING_CAT 0x236u   /* 0x02002229 'Monitoring' */
#define FX6_SLOTID_TECHNICAL 0x237u   /* 0x0200222a 'Technical' */
#define FX6_SLOTID_CINE_EI_SETTING 0x23cu   /* 0x0200225c 'Cine EI Setting' */
#define FX6_SLOTID_BASE_ISO 0x23du   /* 0x02002266 'Base ISO' */
#define FX6_SLOTID_MLUT 0x23eu   /* 0x02002296 'MLUT' */
#define FX6_SLOTID_SET 0x246u   /* 0x020023da 'Set' */
#define FX6_SLOTID_BASE_LOOK 0x247u   /* 0x020023f8 'Base Look' */
#define FX6_SLOTID_RESET_PAINT_SETTINGS 0x248u   /* 0x020023fa 'Reset Paint Settings' */
#define FX6_SLOTID_AUDIO_N2 0x2a4u   /* 0x020041fb 'Audio' */
#define FX6_SLOTID_MAINTENANCE 0x2a7u   /* 0x02004203 'Maintenance' */
#define FX6_SLOTID_MONITORING_ALT 0x2a8u   /* 0x02004205 'Service' */
#define FX6_SLOTID_USER 0x2a9u   /* 0x02004208 'User' */
#define FX6_SLOTID_THUMBNAIL 0x2aau   /* 0x02004209 'Thumbnail' */
#define FX6_SLOTID_TC_MEDIA 0x4ecu   /* 0x0200222b 'TC/Media' */

/* Inverse helper: slot -> canonical ResID (first alias), using the same pair layout. */
#define FX6_RESID_TO_SLOT_ADDR 0x226a6c0u
#define FX6_RESID_TO_SLOT_END  0x2272a80u
#define FX6_SLOTID_TO_ICON_ADDR  0x2272a80u
#define FX6_SLOTID_TO_ICON_END   0x2272f18u

/* Category anchor slots, re-stated here because Phase 8 confirmed them against mapA. */
#define FX6_CAT_SHOOTING   0x234u
#define FX6_CAT_PROJECT    0x235u
#define FX6_CAT_MONITORING 0x236u
#define FX6_CAT_TECHNICAL  0x237u
#define FX6_CAT_TC_MEDIA   0x4ecu
#define FX6_CAT_AUDIO      0x2a4u
#define FX6_CAT_MAINTENANCE 0x2a7u
#define FX6_CAT_USER       0x2a9u
#define FX6_CAT_THUMBNAIL  0x2aau
