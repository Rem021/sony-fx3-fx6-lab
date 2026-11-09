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

/* ======================================================================
 * PHASE 9 — descriptor layouts for view_menu_item / view_icon / view_fill
 * ======================================================================
 * IMPORTANT: two tags from the Phase-9 brief do not exist in this image.
 *
 *   tag 0x042d5798 : 0 descriptors     (searching all 0x48 tables)
 *   tag 0x042d59a8 : 0 descriptors
 *
 * and the two "constructors" named with them are not constructors:
 *
 *   0xc2ad3c   = bl 0xb17620 ; strb w21,[x19,#0x4c0] ...   (inside a body, 0 bl callers)
 *   0xc2993c   = ldp x19,x20,[sp,#0x10] ... ret            (an epilogue,  0 bl callers)
 *
 * The real classes are view_icon tag 0x042d5a50 / ctor 0xc2c188, and view_fill tag 0x042d5a40 /
 * ctor 0xc27698. Both are modelled below; the fictional tags are NOT defined.
 *
 * Descriptor field statistics were measured over every 0x48 row in the image:
 *   view_string    597 rows      view_menu_item 437 rows
 *   view_fill      386 rows      view_icon      256 rows
 */

/* ----------------------------------------------------------------------
 * view_menu_item — tag 0x042d58d0, class ctor 0xc341d4, size 0x19788
 * ----------------------------------------------------------------------
 * Measured field use over all 437 rows:
 *   +0x18  0x00000000 x336, 0x020056e8 x25, 0x02004c46 x18, 0x020023da x13, ...
 *   +0x1c  0x0200a02a x311, 0x00000000 x94, 0x0200a029 x28, 0x0200a02b x4     (layout)
 *   +0x20  0x00000001 x223, 0x00000002 x120, 0x00000000 x94        (MODE 1|2, NOT a colour)
 *   +0x24  0x02006004 x241, 0x00000000 x92, 0x0200600d x40, 0x02006017 x28   (FontName A)
 *   +0x28  0x0200600e x305, 0x00000000 x94, 0x02006016 x30, 0x02006002 x6    (FontName B)
 *   +0x2c  0x00000044 x437                                    (font size, same as view_string)
 *   +0x30  0x00000ce2 x423                                    (flags)
 *   +0x34  0x00002ce9 x437                                    (flags)
 *   +0x38  0x00040008 x21, 0x00050008 x13, 0x00030008 x10, 0x00090019 x9 ...
 *
 * Factory writes (0xc1966c..0xc196b4, x0 = obj+0x1d0):
 *   desc+0x18 -> obj+0x21c   (guarded: skipped when 0)
 *   desc+0x24 -> obj+0x22c   desc+0x28 -> obj+0x234
 *   desc+0x1c -> obj+0x238   desc+0x20 -> obj+0x23c
 *   obj+0x240 = 0
 *   desc+0x38 (u16) -> obj+0x200, only when value <= 0x5b
 *
 * The +0x24/+0x28/+0x1c group is written ONLY if all three are non-zero — the 94 rows with
 * +0x1c == 0 never receive fonts and therefore never render, the same failure shape as Phase 7.
 */
#define FX6_MI_TAG          0x042d58d0u
#define FX6_MI_SIZE         0x19788u
#define FX6_MI_CTOR         0xc341d4u

#define FX6_MI_OBJ_TEXT     0x21cu   /* desc+0x18 */
#define FX6_MI_OBJ_FONT_A   0x22cu   /* desc+0x24 */
#define FX6_MI_OBJ_FONT_B   0x234u   /* desc+0x28 */
#define FX6_MI_OBJ_LAYOUT   0x238u   /* desc+0x1c */
#define FX6_MI_OBJ_MODE     0x23cu   /* desc+0x20, values 0/1/2 */
#define FX6_MI_OBJ_ZERO     0x240u
#define FX6_MI_OBJ_WIDGETID 0x200u   /* desc+0x38, clamped to <= 0x5b */

#define FX6_MI_MODE_NONE    0u
#define FX6_MI_MODE_TEXT    1u
#define FX6_MI_MODE_ICON    2u

typedef struct __attribute__((packed)) {
    uint32_t tag;           /* +0x00  0x042d58d0                            */
    uint32_t zero04;
    uint32_t name;          /* +0x08 */
    uint32_t zero0c;
    uint32_t zero10;
    uint32_t zero14;
    uint32_t text_resid;    /* +0x18 -> obj+0x21c                            */
    uint32_t layout;        /* +0x1c -> obj+0x238                            */
    uint32_t mode;          /* +0x20 -> obj+0x23c   0/1/2                    */
    uint32_t font_a;        /* +0x24 -> obj+0x22c                            */
    uint32_t font_b;        /* +0x28 -> obj+0x234                            */
    uint32_t font_size;     /* +0x2c -> obj+0xa14 (shared with view_string)   */
    uint32_t flag_a;        /* +0x30 */
    uint32_t flag_b;        /* +0x34 */
    uint16_t widget_id;     /* +0x38 -> obj+0x200, <= 0x5b                   */
    uint16_t pad3a;
    uint32_t rect_xy;       /* +0x3c */
    uint32_t rect_wh;       /* +0x40 */
    uint32_t reserved;      /* +0x44 */
} fx6_desc_view_menu_item;  /* sizeof == 0x48 */

/* ----------------------------------------------------------------------
 * view_icon — tag 0x042d5a50, class ctor 0xc2c188, size 0x668
 * ----------------------------------------------------------------------
 * Factory branch (0xc19644..0xc19654): desc+0x18 -> obj+0x21c, and only when non-zero:
 *     0xc19644  ldr w0,[x19,#0x18] ; cbz -> skip ; str w0,[x1,#0x30]
 * The ctor sets +0x1fc = 0 (disabled) and +0x20c (image ResID) is written by the caller, so a
 * view_icon row paints only after +0x1fc = 1 and +0x20c = a namespace-0 image id.
 * The Sprite lives at +0x550; clip colour bytes are +0x21c..+0x21f and the clip size is a u16 pair
 * at +0x204/+0x206 (all measured in round 665).
 */
#define FX6_VI_TAG          0x042d5a50u
#define FX6_VI_SIZE         0x668u
#define FX6_VI_CTOR         0xc2c188u

#define FX6_VI_OBJ_ENABLE   0x1fcu
#define FX6_VI_OBJ_CLIP_RGBA 0x21cu
#define FX6_VI_OBJ_IMAGE    0x20cu
#define FX6_VI_OBJ_CLIP_W   0x204u
#define FX6_VI_OBJ_CLIP_H   0x206u
#define FX6_VI_OBJ_SPRITE   0x550u

typedef struct __attribute__((packed)) {
    uint32_t tag;           /* +0x00  0x042d5a50                            */
    uint32_t zero04;
    uint32_t name;          /* +0x08 */
    uint32_t zero0c;
    uint32_t zero10;
    uint32_t zero14;
    uint32_t image_resid;   /* +0x18 -> obj+0x21c (clip colour) then +0x20c  */
    uint32_t layout;        /* +0x1c */
    uint32_t mode;          /* +0x20 */
    uint32_t font_a;        /* +0x24 */
    uint32_t font_b;        /* +0x28 */
    uint32_t reserved2c;    /* +0x2c */
    uint32_t flag_a;        /* +0x30 */
    uint32_t flag_b;        /* +0x34 */
    uint32_t widget_id;     /* +0x38 */
    uint32_t rect_xy;       /* +0x3c */
    uint32_t rect_wh;       /* +0x40 */
    uint32_t reserved;      /* +0x44 */
} fx6_desc_view_icon;       /* sizeof == 0x48 */

/* ----------------------------------------------------------------------
 * view_fill — tag 0x042d5a40, class ctor 0xc27698, size 0x308
 * ----------------------------------------------------------------------
 * Factory branch (0xc19630..0xc19654, GOT 0x2eedd50 = tag 0x042d5a40):
 *
 *   0xc19644  ldr w0,[x19,#0x18] ; cbz -> skip ; ldr x1,[x21,#0x10] ; str w0,[x1,#0x30]
 *
 * with x1 = obj+0x1d0, so **desc+0x18 lands at obj+0x200**, i.e. straight into the colour-ResID
 * slot that onDrawNotice reads. view_fill is the one class where the descriptor colour needs no
 * translation step. Painting then requires +0x1fc = 1 and either +0x200 != -1 (namespace-6 colour)
 * or the inline bytes +0x205..+0x208.
 */
#define FX6_VF_TAG          0x042d5a40u
#define FX6_VF_SIZE         0x308u
#define FX6_VF_CTOR         0xc27698u

#define FX6_VF_OBJ_ENABLE   0x1fcu
#define FX6_VF_OBJ_COLOR    0x200u
#define FX6_VF_OBJ_RGBA     0x205u
#define FX6_VF_OBJ_SPRITE   0x210u
#define FX6_VF_OBJ_TEXT     0x21cu
#define FX6_VF_OBJ_FONT_A   0x22cu
#define FX6_VF_OBJ_FONT_B   0x234u
#define FX6_VF_OBJ_LAYOUT   0x238u
#define FX6_VF_OBJ_MODE     0x23cu

typedef struct __attribute__((packed)) {
    uint32_t tag;           /* +0x00  0x042d5a40                            */
    uint32_t zero04;
    uint32_t name;          /* +0x08 */
    uint32_t zero0c;
    uint32_t zero10;
    uint32_t zero14;
    uint32_t color_resid;   /* +0x18 -> obj+0x200 (colour ResID, ns 6)        */
    uint32_t layout;        /* +0x1c -> obj+0x238                            */
    uint32_t mode;          /* +0x20 -> obj+0x23c                            */
    uint32_t font_a;        /* +0x24 -> obj+0x22c                            */
    uint32_t font_b;        /* +0x28 -> obj+0x234                            */
    uint32_t font_size;     /* +0x2c -> obj+0xa14                            */
    uint32_t flag_a;        /* +0x30 */
    uint32_t flag_b;        /* +0x34 */
    uint32_t widget_id;     /* +0x38 */
    uint32_t rect_xy;       /* +0x3c */
    uint32_t rect_wh;       /* +0x40 */
    uint32_t reserved;      /* +0x44 */
} fx6_desc_view_fill;       /* sizeof == 0x48 */

/* ----------------------------------------------------------------------
 * Selection highlight colours (color_cmn.uxc, namespace 6). No descriptor field carries these,
 * so they are applied by the presenter at run time.
 * ---------------------------------------------------------------------- */
#define FX6_COLOR_SELECT_ORANGE   0x0200c014u   /* ffaa00ff  selected row       */
#define FX6_COLOR_SELECT_ORANGE2  0x0200c016u   /* ffc000ff  selected variant   */
#define FX6_COLOR_SELECT_RED      0x0200c011u   /* ee0000ff  alert/record       */
#define FX6_COLOR_YELLOW          0x0200c012u   /* ffdd00ff                     */
#define FX6_COLOR_BORDER_GREY     0x0200c00eu   /* 777777ff  separator / border */
#define FX6_COLOR_BORDER_DARK     0x0200c009u   /* 333333ff  outline            */
#define FX6_COLOR_ITEM_BG         0x0200c00du   /* 666666ff  item background    */
#define FX6_COLOR_ITEM_NUMBER_BG  0x0200c00fu   /* aaaaaaff  number plate       */

/* Apply helpers: reproduce the factory's writes plus the paint-enable flags. */
static inline void fx6_menu_item_apply_desc(void *mi, const fx6_desc_view_menu_item *d)
{
    if (!mi || !d) return;
    if (d->text_resid) *(uint32_t *)((char *)mi + FX6_MI_OBJ_TEXT) = d->text_resid;
    if (d->layout && d->font_a && d->font_b) {
        *(uint32_t *)((char *)mi + FX6_MI_OBJ_FONT_A) = d->font_a;
        *(uint32_t *)((char *)mi + FX6_MI_OBJ_FONT_B) = d->font_b;
        *(uint32_t *)((char *)mi + FX6_MI_OBJ_LAYOUT) = d->layout;
        *(uint32_t *)((char *)mi + FX6_MI_OBJ_MODE)   = d->mode;
        *(uint32_t *)((char *)mi + FX6_MI_OBJ_ZERO)   = 0;
    }
    if (d->widget_id <= 0x5bu) *(uint32_t *)((char *)mi + FX6_MI_OBJ_WIDGETID) = d->widget_id;
    *(uint32_t *)((char *)mi + 0xa14) = d->font_size;
    *(int32_t  *)((char *)mi + 0x1e8) = (int32_t)(d->rect_xy & 0xffffu);
    *(int32_t  *)((char *)mi + 0x1ec) = (int32_t)((d->rect_xy >> 16) & 0xffffu);
    *(int32_t  *)((char *)mi + 0x1f0) = (int32_t)(d->rect_wh & 0xffffu);
    *(int32_t  *)((char *)mi + 0x1f4) = (int32_t)((d->rect_wh >> 16) & 0xffffu);
}

static inline void fx6_view_icon_apply_desc(void *ic, const fx6_desc_view_icon *d)
{
    if (!ic || !d) return;
    if (d->image_resid) {
        *(uint32_t *)((char *)ic + FX6_VI_OBJ_CLIP_RGBA) = d->image_resid;
        *(uint32_t *)((char *)ic + FX6_VI_OBJ_IMAGE)     = d->image_resid;
    }
    *(uint16_t *)((char *)ic + FX6_VI_OBJ_CLIP_W) = (uint16_t)(d->rect_wh & 0xffffu);
    *(uint16_t *)((char *)ic + FX6_VI_OBJ_CLIP_H) = (uint16_t)((d->rect_wh >> 16) & 0xffffu);
    *(int32_t  *)((char *)ic + 0x1e8) = (int32_t)(d->rect_xy & 0xffffu);
    *(int32_t  *)((char *)ic + 0x1ec) = (int32_t)((d->rect_xy >> 16) & 0xffffu);
    *(int32_t  *)((char *)ic + 0x1f0) = (int32_t)(d->rect_wh & 0xffffu);
    *(int32_t  *)((char *)ic + 0x1f4) = (int32_t)((d->rect_wh >> 16) & 0xffffu);
    *(uint8_t  *)((char *)ic + FX6_VI_OBJ_ENABLE) = 1;
}

static inline void fx6_view_fill_apply_desc(void *vf, const fx6_desc_view_fill *d)
{
    if (!vf || !d) return;
    if (d->color_resid) {
        *(uint32_t *)((char *)vf + FX6_VF_OBJ_COLOR) = d->color_resid;
    }
    if (d->layout && d->font_a && d->font_b) {
        *(uint32_t *)((char *)vf + FX6_VF_OBJ_FONT_A) = d->font_a;
        *(uint32_t *)((char *)vf + FX6_VF_OBJ_FONT_B) = d->font_b;
        *(uint32_t *)((char *)vf + FX6_VF_OBJ_LAYOUT) = d->layout;
        *(uint32_t *)((char *)vf + FX6_VF_OBJ_MODE)   = d->mode;
    }
    if (d->font_size) *(uint32_t *)((char *)vf + 0xa14) = d->font_size;
    *(int32_t *)((char *)vf + 0x1e8) = (int32_t)(d->rect_xy & 0xffffu);
    *(int32_t *)((char *)vf + 0x1ec) = (int32_t)((d->rect_xy >> 16) & 0xffffu);
    *(int32_t *)((char *)vf + 0x1f0) = (int32_t)(d->rect_wh & 0xffffu);
    *(int32_t *)((char *)vf + 0x1f4) = (int32_t)((d->rect_wh >> 16) & 0xffffu);
    *(uint8_t *)((char *)vf + FX6_VF_OBJ_ENABLE) = 1;
}

/* ======================================================================
 * PHASE 10 — three-layer menu geometry and option-value ResID tables
 * ======================================================================
 * TABLE 0x2ea02f8 is 47 rows = one page of the three-layer menu plus the start of the next page.
 * Measured geometry (x, y, w, h) and roles:
 *
 *   [00] No1_WID_NINEPATCHIMAGE_STAGE1_BG  fill   d18=0x0200c006  (56,49,912,477)   page background
 *   [01] No25_Gridlist                     grid   d18=0             (62,56,494,462)   1st-layer list
 *   [02..09] No35..No28_itemtouchbutton8..1 item  d18=0            (570,463..106,386,52)  2nd-layer rows
 *   [10..16] No9..No4/No10_item*inthesecondlayer str d18=0        (578,418..163/469,370,40) 3rd-layer rows
 *   [17] No21_ItemBG                       fill   d18=0x0200c00d  (564,62,401,36)   header bar
 *   [18] No3_Backstringinthesecondlayer    str    d18=0x02004c3e  (622,112,326,40)  "Back"
 *   [19] No23_Itemselectionofthefirstlayer str    d18=0            (568,62,280,36)  1st-layer selection
 *   [20] No16_Loweroutsideline2            fill   d18=0x0200c009  (58,524,910,2)
 *   [21] No15_Loweroutsideline             fill   d18=0x0200c005  (57,523,908,2)
 *   [22] No12_Upperoutsideline2            fill   d18=0x0200c00a  (59,50,908,2)
 *   [23] No26_ScrollbarBase                fill   d18=0x0200c005  (958,102,4,415)
 *   [24] No27_Scrollbar                    fill   d18=0x0200c013  (958,102,4,415)
 *   [25] No2_Backiconinthesecondlayer      icon   d18=0x02000154  (578,112,38,38)   back arrow
 *   [26] No22_ItemnumberBG                 fill   d18=0x0200c00f  (921,66,40,28)
 *   [27] No24_Itemnumber                   str    d18=0            (922,67,38,28)
 *   [28] No18_Rightoutsideline2            fill   d18=0x0200c00a  (965,52,2,473)
 *   [29] No14_Leftoutsideline2             fill   d18=0x0200c00a  (57,50,2,473)
 *   [30] No20_Separator2                   fill   d18=0x0200c00e  (562,52,2,471)   column divider
 *   [31] No19_Separator                    fill   d18=0x0200c001  (560,52,2,471)   column divider
 *   [32] No11_Upperoutsideline             fill   d18=0x0200c009  (57,49,910,1)
 *   [33] No17_Rightoutsideline             fill   d18=0x0200c009  (967,49,1,477)
 *   [34] No13_Leftoutsideline              fill   d18=0x0200c009  (56,49,1,477)
 *   [35] page break 0x42d5a60              (0,0,0,0)
 *   [36] No69_TOUCH_SCREEN                 (0,0,1024,540)
 *   [37] No1_Backgroundleft                fill d18=0x0200c006 (56,49,482,477)   next page
 *   [38] No21_Backgroundright              fill d18=0x0200c006 (542,49,426,477)
 *   [39] No58_Gridlist                     grid d18=0           (126,102,403,415)
 *   [40..46] No68..No62_itemtouchbutton10..4 item d18=0         (546,493..229,418,44)
 *
 * So the three columns are geometrically:
 *   1st layer   x 56..560     (list at 62,56 494x462; divider 560/562; selection bar 568,62 280x36)
 *   2nd layer   x 564..985    (buttons 570..956, w 386 h 52; back icon 578,112 38x38)
 *   3rd layer   x 578..948    (rows 578, w 370 h 40, y 163..509 - step 51)
 *   header      y 49..98      (top lines 49/50, header bar 564,62 401x36, page border 477 tall)
 *
 * Table 0x2eaf208 (17 rows) is the Setting centre page, not the layered menu:
 *   [00] touch, [01] No1_BG fill c001 (96,72,768,432), [02] No28_BG fill c008 (96,194,768,188),
 *   [03] No8_CENTER_VALUE str (310,269,530,32), [04] No7_CENTER_TITLE str d18=0x02002fea 'Look'
 *   (154,269,148,32), [05..10] six separators c00e, [11..16] the six big cells (view_menu_item).
 */
typedef struct {
    int16_t  x, y;
    uint16_t w, h;
} fx6_rect_t;

typedef struct {
    const char *name;
    uint32_t tag;
    fx6_rect_t rect;
    uint32_t resid;        /* desc+0x18, 0 when unused */
    uint8_t  layer;        /* 0 = chrome, 1..3 = column */
} fx6_menu_row_t;

static const fx6_menu_row_t fx6_three_layer_rows[] = {
    /* name                                 tag          x     y     w    h    resid        layer */
    {"No1_WID_NINEPATCHIMAGE_STAGE1_BG",   0x042d5a40u, { 56,  49, 912, 477}, 0x0200c006u, 0},
    {"No25_Gridlist",                      0x042d59e0u, { 62,  56, 494, 462}, 0x00000000u, 1},
    {"No35_itemtouchbutton8",              0x042d58d0u, {570, 463, 386,  52}, 0x00000000u, 2},
    {"No34_itemtouchbutton7",              0x042d58d0u, {570, 412, 386,  52}, 0x00000000u, 2},
    {"No33_itemtouchbutton6",              0x042d58d0u, {570, 361, 386,  52}, 0x00000000u, 2},
    {"No32_itemtouchbutton5",              0x042d58d0u, {570, 310, 386,  52}, 0x00000000u, 2},
    {"No31_itemtouchbutton4",              0x042d58d0u, {570, 259, 386,  52}, 0x00000000u, 2},
    {"No30_itemtouchbutton3",              0x042d58d0u, {570, 208, 386,  52}, 0x00000000u, 2},
    {"No29_itemtouchbutton2",              0x042d58d0u, {570, 157, 386,  52}, 0x00000000u, 2},
    {"No28_itemtouchbutton1",              0x042d58d0u, {570, 106, 386,  52}, 0x00000000u, 2},
    {"No9_item6inthesecondlayer",          0x042d57f0u, {578, 418, 370,  40}, 0x00000000u, 3},
    {"No8_item5inthesecondlayer",          0x042d57f0u, {578, 367, 370,  40}, 0x00000000u, 3},
    {"No7_item4inthesecondlayer",          0x042d57f0u, {578, 316, 370,  40}, 0x00000000u, 3},
    {"No6_item3inthesecondlayer",          0x042d57f0u, {578, 265, 370,  40}, 0x00000000u, 3},
    {"No5_item2inthesecondlayer",          0x042d57f0u, {578, 214, 370,  40}, 0x00000000u, 3},
    {"No4_item1inthesecondlayer",          0x042d57f0u, {578, 163, 370,  40}, 0x00000000u, 3},
    {"No10_item7inthesecondlayer",         0x042d57f0u, {578, 469, 370,  40}, 0x00000000u, 3},
    {"No21_ItemBG",                        0x042d5a40u, {564,  62, 401,  36}, 0x0200c00du, 0},
    {"No3_Backstringinthesecondlayer",     0x042d57f0u, {622, 112, 326,  40}, 0x02004c3eu, 0},
    {"No23_Itemselectionofthefirstlayer",  0x042d57f0u, {568,  62, 280,  36}, 0x00000000u, 0},
    {"No16_Loweroutsideline2",             0x042d5a40u, { 58, 524, 910,   2}, 0x0200c009u, 0},
    {"No15_Loweroutsideline",              0x042d5a40u, { 57, 523, 908,   2}, 0x0200c005u, 0},
    {"No12_Upperoutsideline2",             0x042d5a40u, { 59,  50, 908,   2}, 0x0200c00au, 0},
    {"No26_ScrollbarBase",                 0x042d5a40u, {958, 102,   4, 415}, 0x0200c005u, 0},
    {"No27_Scrollbar",                     0x042d5a40u, {958, 102,   4, 415}, 0x0200c013u, 0},
    {"No2_Backiconinthesecondlayer",       0x042d5a50u, {578, 112,  38,  38}, 0x02000154u, 0},
    {"No22_ItemnumberBG",                  0x042d5a40u, {921,  66,  40,  28}, 0x0200c00fu, 0},
    {"No24_Itemnumber",                    0x042d57f0u, {922,  67,  38,  28}, 0x00000000u, 0},
    {"No18_Rightoutsideline2",             0x042d5a40u, {965,  52,   2, 473}, 0x0200c00au, 0},
    {"No14_Leftoutsideline2",              0x042d5a40u, { 57,  50,   2, 473}, 0x0200c00au, 0},
    {"No20_Separator2",                    0x042d5a40u, {562,  52,   2, 471}, 0x0200c00eu, 0},
    {"No19_Separator",                     0x042d5a40u, {560,  52,   2, 471}, 0x0200c001u, 0},
    {"No11_Upperoutsideline",              0x042d5a40u, { 57,  49, 910,   1}, 0x0200c009u, 0},
    {"No17_Rightoutsideline",              0x042d5a40u, {967,  49,   1, 477}, 0x0200c009u, 0},
    {"No13_Leftoutsideline",               0x042d5a40u, { 56,  49,   1, 477}, 0x0200c009u, 0},
};
#define FX6_THREE_LAYER_COUNT (sizeof(fx6_three_layer_rows)/sizeof(fx6_three_layer_rows[0]))

/* Column geometry, derived from the table above (constants, so a probe can lay out its own rows). */
#define FX6_L1_X        62
#define FX6_L1_Y        56
#define FX6_L1_W        494
#define FX6_L1_H        462
#define FX6_L2_X        570
#define FX6_L2_Y0       106
#define FX6_L2_W        386
#define FX6_L2_H        52
#define FX6_L2_STEP     51          /* 463-412 = 412-361 = ... */
#define FX6_L3_X        578
#define FX6_L3_Y0       163
#define FX6_L3_W        370
#define FX6_L3_H        40
#define FX6_L3_STEP     51
#define FX6_DIVIDER_X1  560
#define FX6_DIVIDER_X2  562
#define FX6_BACKICON_X  578
#define FX6_BACKICON_Y  112
#define FX6_BACKICON_WH 38
#define FX6_SCROLL_X    958
#define FX6_SCROLL_Y    102
#define FX6_SCROLL_W    4
#define FX6_SCROLL_H    415

/* ----------------------------------------------------------------------
 * Group 1: Shooting -> {FPS, Shutter, ISO/Gain, ND Filter, LUT/Color, S&Q}
 * All ResIDs below were resolved from the two string containers; note that many option
 * families store the same text twice (long and short form), e.g. 0x4970 and 0x4971 are both
 * '59.94'. Use the FIRST of each pair for a 2nd-layer value row.
 * ---------------------------------------------------------------------- */
typedef struct { uint32_t resid; const char *text; } fx6_opt_t;

static const fx6_opt_t fx6_opt_fps[] = {          /* ns2 */
    {0x02004970u, "59.94"}, {0x02004972u, "50"},    {0x02004974u, "29.97"},
    {0x02004976u, "25"},    {0x02004978u, "24"},    {0x0200497au, "23.98"},
    {0x0200497cu, "Custom"},{0x0200497eu, "Cine EI"},
};
static const fx6_opt_t fx6_opt_fps_hfr[] = {      /* ns1 high frame rate */
    {0x02002b3eu, "119.88"},{0x02002b99u, "119.88P"},{0x02002b2eu, "100"},
    {0x02002b37u, "100P"},
};
static const fx6_opt_t fx6_opt_shutter[] = {      /* ns2 */
    {0x02004729u, "1/100"}, {0x0200472bu, "1/150"}, {0x0200472du, "1/200"},
    {0x0200472fu, "1/250"}, {0x02004726u, "T2.8"},  {0x02004727u, "T4"},
    {0x02004728u, "T5.6"},  {0x02004731u, "T8"},    {0x02004732u, "T11"},
    {0x02004733u, "T16"},
};
static const fx6_opt_t fx6_opt_iso[] = {          /* ns2, long form */
    {0x020046c8u, "ISO 640"},  {0x020046cau, "ISO 800"},  {0x020046ccu, "ISO 1000"},
    {0x020046ceu, "ISO 1250"}, {0x020046d0u, "ISO 1600"}, {0x020046d2u, "ISO 2000"},
    {0x020046d4u, "ISO 2500"}, {0x020046d6u, "ISO 3200"}, {0x020046d8u, "ISO 4000"},
    {0x020046dau, "ISO 5000"}, {0x020046dcu, "ISO 6400"}, {0x020046deu, "ISO 8000"},
    {0x020046e0u, "ISO 10000"},
};
static const fx6_opt_t fx6_opt_nd[] = {           /* ns2 */
    {0x02004027u, "ND: Clear"}, {0x02004028u, "ND: 0.9"}, {0x02004029u, "ND: 1.8"},
    {0x0200406au, "ND: Off"},   {0x0200406bu, "ND: 1"},   {0x0200406cu, "ND: 2"},
    {0x0200406du, "ND: 3"},
};
static const fx6_opt_t fx6_opt_white_balance[] = { /* ns2 */
    {0x0200402au, "White: Preset"}, {0x0200402bu, "White: Memory"},
    {0x0200402cu, "White: A"},      {0x0200402du, "White: B"},
    {0x0200402eu, "White: ATW"},    {0x0200402fu, "White Balance Preset"},
};
static const fx6_opt_t fx6_opt_sq[] = {           /* ns2, S&Q motion toggles */
    {0x02004742u, "S&Q Motion: On"},  {0x02004743u, "S&Q Motion: Off"},
    {0x02004744u, "Interval Rec: On"},{0x02004745u, "Interval Rec: Off"},
    {0x02004746u, "Picture Cache Rec: On"}, {0x02004747u, "Picture Cache Rec: Off"},
    {0x02004748u, "Clip Continuous Rec: On"}, {0x02004749u, "Clip Continuous Rec: Off"},
    {0x0200474au, "Simul Rec: On"},   {0x0200474bu, "Simul Rec: Off"},
    {0x0200474cu, "4K & HD (Sub) Rec: On"}, {0x0200474du, "4K & HD (Sub) Rec: Off"},
    {0x0200474eu, "Proxy Rec: On"},   {0x0200474fu, "Proxy Rec: Off"},
};

/* ----------------------------------------------------------------------
 * Group 2: Paint/Look -> Base Look -> real option values.
 * The 9-entry gamma/look list at .rodata 0x2384ba8 is the authoritative ordered set.
 * ---------------------------------------------------------------------- */
static const fx6_opt_t fx6_opt_base_look[] = {
    {0x020023f1u, "HLG Live"},   {0x020024acu, "HLG Mild"},  {0x020023f5u, "HLG Natural"},
    {0x02002460u, "S-Log3"},     {0x02002464u, "S-Cinetone"},{0x02002466u, "Standard"},
    {0x020023e9u, "Still"},      {0x020023edu, "ITU709"},    {0x02002a19u, "709tone"},
};
/* s709 / 709(800%) family (ns1), used by the "Look" column rather than Base Look. */
static const fx6_opt_t fx6_opt_look_s709[] = {
    {0x0200219fu, "S-Log3"}, {0x020021a0u, "s709"}, {0x0200219eu, "709(800%)"},
};
/* MLUT / LUT list (ns1) */
static const fx6_opt_t fx6_opt_lut[] = {
    {0x0200201cu, "LUT s709"}, {0x0200201du, "LUT 709"}, {0x0200201eu, "LUT HG7"},
    {0x0200201fu, "LUT HG8"},  {0x02002020u, "LUT S-Log3"}, {0x02002029u, "MLUT"},
    {0x0200202bu, "SDR(Off)"}, {0x0200202cu, "SDR(S-Log2)"}, {0x0200202du, "SDR(S-Log3)"},
};
/* Gamma display assist conversions (ns2) */
static const fx6_opt_t fx6_opt_gamma_assist[] = {
    {0x020042e5u, "HLG1"}, {0x020042e7u, "HLG2"}, {0x020042e9u, "709(800%"},
    {0x020042eau, "HLG-709(800%)"}, {0x020042ebu, "HLG-709"},
    {0x020042ecu, "S-Log3-709(800%)"}, {0x020042edu, "S-Log3-"},
};
/* Cine EI exposure index steps (ns1) */
static const fx6_opt_t fx6_opt_cine_ei[] = {
    {0x0200203bu, "250EI / 4.0E"}, {0x0200203cu, "320EI / 4.3E"},
    {0x0200203du, "400EI / 4.7E"}, {0x0200203eu, "500EI / 5.0E"},
    {0x0200203fu, "640EI / 5.3E"}, {0x02002040u, "800EI / 5.7E"},
};

/* Layer-2 item labels for the Shooting column (these are the 2nd-layer rows, not values). */
static const fx6_opt_t fx6_shooting_items[] = {
    {0x02005082u, "FPS"},          {0x020050e8u, "Shutter"},
    {0x02004c32u, "ISO"},          {0x0200420eu, "Gain"},
    {0x02004288u, "ND Filter"},    {0x020029f8u, "Look"},
    {0x02004246u, "S&Q Motion"},
};
/* Layer-2 item labels for the Paint/Look column. */
static const fx6_opt_t fx6_paint_items[] = {
    {0x020023f8u, "Base Look"},    {0x02002296u, "MLUT"},
    {0x02002266u, "Base ISO"},     {0x0200225cu, "Cine EI Setting"},
    {0x02005689u, "White Balance"},{0x020023fau, "Reset Paint Settings"},
};

#define FX6_OPT_COUNT(a) (sizeof(a)/sizeof((a)[0]))

/* ======================================================================
 * PHASE 11 — the eleven top-level categories, plain and PUA-prefixed
 * ======================================================================
 * All 22 ids below were resolved individually against string_english.uxc (ns1) and
 * string_english_2.uxc (ns2); none is inferred. Note the mixture: five categories exist only as
 * plain text (Shooting, Paint/Look, TC/Media, Technical, Edit User Menu), the rest have a second
 * copy in a PUA-prefixed "icon + label" form.
 *
 * The PUA glyphs are the category icons rendered from the font, e.g. \ue60a, \ue60f, \ue60b,
 * \ue60e, \ue612, \ue618, \ue6b9 -- so a row that shows the prefixed string needs no separate
 * view_icon child.
 */
typedef struct {
    const char *name;
    uint32_t resid_plain;   /* bare label                */
    uint32_t resid_pua;     /* \ueXXX-prefixed label, 0 if the container has no such variant */
    uint8_t  ns_plain;
} fx6_top_category_t;

static const fx6_top_category_t fx6_top_categories[11] = {
    {"User",          0x02004208u, 0x00000000u, 2},   /* ns2 'User'                     */
    {"Edit User Menu",0x02004d4au, 0x00000000u, 2},   /* ns2 'Edit User Menu'           */
    {"Shooting",      0x02002227u, 0x00000000u, 1},   /* ns1 'Shooting'                 */
    {"Project",       0x02002228u, 0x020024d4u, 1},   /* ns1 'Project',  \ue60bProject  */
    {"Paint/Look",    0x02002493u, 0x00000000u, 1},   /* ns1 'Paint/Look'               */
    {"TC/Media",      0x0200222bu, 0x00000000u, 1},   /* ns1 'TC/Media'                 */
    {"Monitoring",    0x02002229u, 0x020024d6u, 1},   /* ns1, \ue60eMonitoring          */
    {"Audio",         0x020041fbu, 0x020024d2u, 2},   /* ns2, \ue60fAudio               */
    {"Thumbnail",     0x02004209u, 0x00000000u, 2},   /* ns2 'Thumbnail'                */
    {"Technical",     0x0200222au, 0x00000000u, 1},   /* ns1 'Technical'                */
    {"Maintenance",   0x02004203u, 0x02002cdbu, 2},   /* ns2, \ue6b9Maintenance         */
};
#define FX6_TOP_CATEGORY_COUNT 11u

/* Additional PUA-prefixed variants found in the containers that are NOT top-level categories but
 * appear in the same icon family. Useful when a navigation column mixes categories and panels. */
#define FX6_PUA_CAMERA      0x020024d0u   /* \ue60aCamera      */
#define FX6_PUA_CAMERA_ALT  0x020024d1u
#define FX6_PUA_AUDIO       0x020024d2u   /* \ue60fAudio       */
#define FX6_PUA_AUDIO_ALT   0x020024d3u
#define FX6_PUA_PROJECT     0x020024d4u   /* \ue60bProject     */
#define FX6_PUA_PROJECT_ALT 0x020024d5u
#define FX6_PUA_MONITORING  0x020024d6u   /* \ue60eMonitoring  */
#define FX6_PUA_MONITORING_ALT 0x020024d7u
#define FX6_PUA_MEDIA       0x020024dcu   /* \ue618Media       */
#define FX6_PUA_NETWORK     0x020024e0u   /* \ue612Network     */
#define FX6_PUA_MAINTENANCE 0x02002cdbu   /* \ue6b9Maintenance */
#define FX6_PUA_MONITORING_2 0x02002b11u

/* ======================================================================
 * PHASE 11 — the two list containers are NOT built by the factory
 * ======================================================================
 * Tag 0x042d59e0 (No25_Gridlist) and 0x042d5a20 (No4_SETTING_LIST_MAIN) never appear in the
 * factory's tag dispatch. The factory only compares these nine tags:
 *
 *   0xc19534 GOT 0x2ee56f8 -> 0x42d5a50   view_icon
 *   0xc19584 GOT 0x2ee6468 -> 0x42d57f0   view_string
 *   0xc195dc GOT 0x2ee6ab0 -> 0x42d59a0
 *   0xc19634 GOT 0x2eedd50 -> 0x42d5a40   view_fill
 *   0xc1965c GOT 0x2eeb738 -> 0x42d58d0   view_menu_item
 *   0xc196bc GOT 0x2ee77d8 -> 0x42d5840
 *   0xc19708 GOT 0x2ee6318 -> 0x42d5960
 *   0xc19754 GOT 0x2ee2f00 -> 0x42d57d0
 *   0xc19768 GOT 0x2ee25b0 -> 0x42d57e0
 *
 * Instead the containers are built by the list constructor appFw+0xc870cc(this, desc*, u32 count):
 *
 *   0xc870ec  str  wzr,[x19,#0x648]        ; count = 0
 *   0xc870f0  mov  x2,#0x640
 *   0xc87104  str  x0,[x19]                ; vptr from GOT 0x2eece18
 *   0xc87114  bl   0xb174d0                ; memset(this+8, 0, 0x640)
 *   0xc87118  cmp  x23,x22                 ; loop over count descriptions
 *   0xc87120  ldr  x0,[x20]                ; desc[i]
 *   0xc8712c  bl   0xc87054                ; filter: accept only these row classes
 *   0xc87138  ubfiz x0,x21,#4,#32          ; row slot = i*0x10
 *   0xc87148  str  x1,[x0,#8]              ; rows[i].view   = desc[i] tag target
 *   0xc8714c  ldrh w1,[x20,#0x3a]
 *   0xc87150  str  w1,[x0,#0x10]           ; rows[i].id     = desc[i]+0x3a (u16 row id)
 *   0xc87164  str  w21,[x19,#0x648]        ; stored count
 *   0xc87168  str  xzr,[x19,#0x650]        ; cursor = NULL
 *
 * so the row array is **stride 0x10** at this+8: { void *view; u32 id; u32 pad }, and the visible
 * row count is decided at run time by how many descriptions pass the filter at 0xc87054 — it is not
 * a compile-time constant. That is why no fixed "how many row children" number exists in the image.
 *
 * Cursor / selection support (same class, immediately after the ctor):
 *
 *   0xc8717c  str  x1,[x0,#0x650]     set cursor object
 *   0xc87184  ldr  x0,[x0,#0x650] ; cbz ; ldr w0,[x0]      cursor index, 0 when unset
 *   0xc8719c  ubfiz x1,x1,#4,#32 ; add x1,x0,x1 ; ldr w19,[x1,#0x10] ; ldr x1,[x1,#8]
 *   0xc87200  bl   0xc86f4c           row -> param_t
 *   0xc87204  strb w21,[x0,#0x3c]     selected flag
 *   0xc87210  bl   0xc86f4c
 *   0xc87218  strb w23,[x0,#0x6c]     per-row state byte (at param+0x106c)
 *
 * The cursor colour is therefore NOT stored in the container: the selection is expressed as a byte
 * at `param_t + 0x3c` (and `+0x106c` for the secondary state), with the actual colour coming from
 * the row widget's own sprite. Consistent with round 677: no descriptor carries `0x0200c0xx`.
 */
/* The filter 0xc87054 accepts exactly five row-class tags (GOT slot -> tag):
 *   0x2eeb738 -> 0x042d58d0  view_menu_item          (the normal list row)
 *   0x2ee3cc8 -> 0x042d5850  another row class
 *   0x2eee168 -> 0x042d58f0  another row class
 *   0x2ee6ab0 -> 0x042d59a0  another row class
 *   0x2ee9180 -> 0x042d5a20  view_list_scroll_cursor_fixed (nested list as a row)
 * Anything else in the description array is skipped, so the stored count at +0x648 can be smaller
 * than the number of descriptions passed in.
 */
#define FX6_CONTAINER_CTOR      0xc870ccu
#define FX6_CONTAINER_VPTR_GOT  0x2eece18u   /* -> static vtable 0x2d58950 */
#define FX6_CONTAINER_ROW_OFF   0x8u
#define FX6_CONTAINER_ROW_STRIDE 0x10u
#define FX6_CONTAINER_ROW_ID_OFF 0x3au   /* source field inside the descriptor */
#define FX6_CONTAINER_COUNT     0x648u
#define FX6_CONTAINER_CURSOR    0x650u
#define FX6_CONTAINER_ROWS_MAX  (0x640u / FX6_CONTAINER_ROW_STRIDE)   /* 100 slots */

#define FX6_ROW_SELECTED_BYTE   0x3cu    /* param_t + 0x3c  = selected flag      */
#define FX6_ROW_STATE_BYTE      0x106cu  /* param_t + 0x106c = secondary state   */

/* The two container tags, with their on-screen rects from the tables. */
#define FX6_GRIDLIST_TAG        0x042d59e0u
#define FX6_GRIDLIST_RECT       {62, 56, 494, 462}
#define FX6_SETTING_LIST_TAG    0x042d5a20u
#define FX6_SETTING_LIST_RECT   {96, 72, 402, 432}

/* ======================================================================
 * PHASE 12 — TABLE 0x2ea3e50 and TABLE 0x2eaf208 as static row arrays
 * ====================================================================== */

/* Setting main page, TABLE 0x2ea3e50 rows 0..9 (row 10 is the page break 0x42d5a60). */
static const fx6_menu_row_t fx6_setting_main_rows[] = {
    {"No107_BLOCK_TOUCH",       0x042d5860u, {  0,  0,1024,540}, 0x00000000u, 0},
    {"No4_SETTING_LIST_MAIN",   0x042d5a20u, { 96, 72, 402,432}, 0x00000000u, 1},
    {"No20_SETTING_MAIN_STRING",0x042d57f0u, {139,270, 348, 36}, 0x00000000u, 2},
    {"No3_SETTING_VALUE",       0x042d57f0u, {505,266, 315, 36}, 0x00000000u, 3},
    {"No32_SETTING_VALUE2",     0x042d57f0u, {505,266, 308, 32}, 0x00000000u, 3},
    {"No2_SETTING_ITEM",        0x042d57f0u, {505,236, 315, 28}, 0x00000000u, 2},
    {"No106_BUTTON_BOTTOM_RIGHT", 0x042d58d0u, {654,425, 164, 72}, 0x020023dau, 0},
    {"No105_BUTTON_BOTTOM_CENTER",0x042d58d0u, {398,425, 164, 72}, 0x020023dau, 0},
    {"No103_BUTTON_TOP_RIGHT",    0x042d58d0u, {654, 80, 164, 72}, 0x020023dau, 0},
    {"No102_BUTTON_TOP_CENTER",   0x042d58d0u, {398, 80, 164, 72}, 0x020023dau, 0},
};
#define FX6_SETTING_MAIN_COUNT (sizeof(fx6_setting_main_rows)/sizeof(fx6_setting_main_rows[0]))

/* Setting centre page, TABLE 0x2eaf208 rows 0..16 — the 2x3 grid of six big cells. */
static const fx6_menu_row_t fx6_setting_center_rows[] = {
    {"No107_BLOCK_TOUCH",  0x042d5860u, {  0,  0,1024,540}, 0x00000000u, 0},
    {"No1_BG",             0x042d5a40u, { 96, 72, 768,432}, 0x0200c001u, 0},
    {"No28_BG",            0x042d5a40u, { 96,194, 768,188}, 0x0200c008u, 0},
    {"No8_CENTER_VALUE",   0x042d57f0u, {310,269, 530, 32}, 0x00000000u, 0},
    {"No7_CENTER_TITLE",   0x042d57f0u, {154,269, 148, 32}, 0x02002feau, 0},
    {"No34_SEPARATOR",     0x042d5a40u, { 96,382, 768,  4}, 0x0200c00eu, 0},
    {"No33_SEPARATOR",     0x042d5a40u, { 96,190, 768,  4}, 0x0200c00eu, 0},
    {"No32_SEPARATOR",     0x042d5a40u, {607,386,   4,118}, 0x0200c00eu, 0},
    {"No31_SEPARATOR",     0x042d5a40u, {349,386,   4,118}, 0x0200c00eu, 0},
    {"No30_SEPARATOR",     0x042d5a40u, {607, 72,   4,118}, 0x0200c00eu, 0},
    {"No29_SEPARATOR",     0x042d5a40u, {349, 72,   4,118}, 0x0200c00eu, 0},
    {"No101_BUTTON_01",    0x042d58d0u, { 96, 72, 257,122}, 0x00000000u, 0},
    {"No102_BUTTON_02",    0x042d58d0u, {349, 72, 262,122}, 0x00000000u, 0},
    {"No103_BUTTON_03",    0x042d58d0u, {607, 72, 257,122}, 0x00000000u, 0},
    {"No104_BUTTON_04",    0x042d58d0u, { 96,382, 257,122}, 0x00000000u, 0},
    {"No105_BUTTON_05",    0x042d58d0u, {349,382, 262,122}, 0x00000000u, 0},
    {"No106_BUTTON_06",    0x042d58d0u, {607,382, 257,122}, 0x00000000u, 0},
};
#define FX6_SETTING_CENTER_COUNT (sizeof(fx6_setting_center_rows)/sizeof(fx6_setting_center_rows[0]))

/* ======================================================================
 * PHASE 12 — 2nd-layer item labels for the remaining categories
 * ======================================================================
 * IMPORTANT: unlike fx6_opt_base_look (taken from a real .rodata ResID run), these five arrays are
 * NOT backed by a single contiguous table in the image. Each id below was looked up individually and
 * its text confirmed, but the ORDER is the natural FX6 menu order, not an order recovered from
 * .rodata. Treat the ordering as conventional, the ids as verified.
 *
 * The bulk of the labels come from one contiguous block in string_english_2.uxc, 0x4230..0x42a0 —
 * that block is the real "secondary menu label" pool and is worth reading in full when wiring more
 * categories (it includes Audio Input/Level/Output, Output Format/Setting, Monitor LUT, LCD/VF
 * Setting, Peaking/Marker/Zebra, Timecode/Users Bit/TC Display, S&Q/Interval/Cache/Simul Rec,
 * Update/Format Media, All/Scene File, Base Setting, Rec Format, Codec, Genlock, Language, Clock Set,
 * All Reset, Version, Network Reset, ...).
 */
static const fx6_opt_t fx6_project_items[] = {
    {0x0200425eu, "Base Setting"},
    {0x0200425fu, "Rec Format"},
    {0x02004261u, "Codec"},
    {0x0200225cu, "Cine EI Setting"},
    {0x0200424fu, "Simul Rec"},
    {0x020042d0u, "Proxy Rec"},
    {0x0200424cu, "Picture Cache Rec"},
    {0x02004247u, "Interval Rec"},
    {0x02004246u, "S&Q Motion"},
    {0x02004249u, "Clip Continuous Rec"},
    {0x02004264u, "Assignable Button"},
    {0x02004262u, "Genlock"},
    {0x0200425du, "System Setting"},
    {0x0200425cu, "ND Adjustment"},
};
static const fx6_opt_t fx6_monitoring_items[] = {
    {0x02004238u, "Output Setting"},
    {0x02004236u, "Output Format"},
    {0x02004235u, "Output On/Off"},
    {0x02004234u, "Audio Output"},
    {0x02004239u, "Monitor LUT"},
    {0x0200423au, "Output Display"},
    {0x02004241u, "Display On/Off"},
    {0x0200423bu, "LCD Setting"},
    {0x0200423cu, "VF Setting"},
    {0x0200423du, "Peaking"},
    {0x0200423eu, "Marker"},
    {0x0200423fu, "Zebra"},
    {0x020042dcu, "Gamma Display Assist"},
    {0x02002223u, "VF Adjust"},
    {0x02005564u, "LCD/VF Adjust"},
    {0x02004f18u, "HDMI Output"},
};
static const fx6_opt_t fx6_audio_items[] = {
    {0x02004232u, "Audio Input"},
    {0x02004233u, "Audio Level"},
    {0x02004234u, "Audio Output"},
    {0x02002192u, "Volume"},
    {0x02002191u, "Headphone Out"},
    {0x02003132u, "Wind Filter"},
    {0x0200429fu, "WRR Setting"},
    {0x02004285u, "Iris"},
};
static const fx6_opt_t fx6_tc_media_items[] = {
    {0x02004242u, "Timecode"},
    {0x02004243u, "Users Bit"},
    {0x02004244u, "TC Display"},
    {0x02004245u, "HDMI TC Out"},
    {0x02002244u, "Clip Name Format"},
    {0x02004253u, "Update Media"},
    {0x02004254u, "Format Media"},
    {0x02004255u, "All File"},
    {0x02004256u, "Scene File"},
    {0x02004258u, "Planning Metadata"},
};
static const fx6_opt_t fx6_maintenance_items[] = {
    {0x0200426bu, "Language"},
    {0x0200426cu, "Clock Set"},
    {0x0200426du, "Country"},
    {0x0200426eu, "Hours Meter"},
    {0x0200426fu, "Network"},
    {0x02004270u, "Wi-Fi"},
    {0x02004291u, "Network Reset"},
    {0x02004271u, "All Reset"},
    {0x02004272u, "Option"},
    {0x02004273u, "Version"},
    {0x0200426au, "GPS"},
    {0x02004267u, "Display Mode"},
};

/* Index of the eleven categories -> the 2nd-layer array to show for it, for a table-driven column. */
typedef struct {
    uint32_t category_resid;
    const fx6_opt_t *items;
    uint32_t count;
} fx6_category_map_t;

#define FX6_CATMAP_ENTRY(cat, arr) { (cat), (arr), (uint32_t)FX6_OPT_COUNT(arr) }

static const fx6_category_map_t fx6_category_map[] = {
    FX6_CATMAP_ENTRY(0x02002227u, fx6_shooting_items),     /* Shooting     */
    FX6_CATMAP_ENTRY(0x02002228u, fx6_project_items),      /* Project      */
    FX6_CATMAP_ENTRY(0x02002493u, fx6_paint_items),        /* Paint/Look   */
    FX6_CATMAP_ENTRY(0x0200222bu, fx6_tc_media_items),     /* TC/Media     */
    FX6_CATMAP_ENTRY(0x02002229u, fx6_monitoring_items),   /* Monitoring   */
    FX6_CATMAP_ENTRY(0x020041fbu, fx6_audio_items),        /* Audio        */
    FX6_CATMAP_ENTRY(0x02004203u, fx6_maintenance_items),  /* Maintenance  */
};
#define FX6_CATEGORY_MAP_COUNT (sizeof(fx6_category_map)/sizeof(fx6_category_map[0]))

/* ======================================================================
 * PHASE 13 — the remaining four categories, completing all eleven
 * ====================================================================== */

static const fx6_opt_t fx6_technical_items[] = {
    {0x0200420eu, "Gain"},
    {0x020050e8u, "Shutter"},
    {0x02004285u, "Iris"},
    {0x02004212u, "Focus"},
    {0x02004211u, "Auto Exposure"},
    {0x02005689u, "White Balance"},
    {0x02004229u, "Detail"},
    {0x0200422au, "Aperture"},
    {0x0200290au, "SteadyShot"},
    {0x02004214u, "Flicker Reduce"},
    {0x02004215u, "Flash Band Reduce"},
    {0x02002e6du, "Color Bars"},
    {0x0200425au, "Test Saw"},
    {0x02004218u, "Lens Interface"},
    {0x02004288u, "ND Filter"},
    {0x02004210u, "Slow Shutter"},
    {0x02004217u, "Image Inversion"},
};
static const fx6_opt_t fx6_thumbnail_items[] = {
    {0x02004209u, "Thumbnail"},
    {0x02004ff3u, "Clip"},
    {0x0200410du, "Shot Mark"},
    {0x020028e8u, "Essence Mark"},
    {0x020042c7u, "Index Picture"},
    {0x02004fddu, "Delete Clip"},
    {0x02004ff8u, "TC Index"},
    {0x02004fffu, "Video Codec"},
    {0x02005001u, "Audio Codec"},
    {0x0200500cu, "Clip Properties"},
};
static const fx6_opt_t fx6_user_items[] = {
    {0x02004294u, "User Menu Item"},
    {0x02004d4au, "Edit User Menu"},
    {0x02004264u, "Assignable Button"},
    {0x02004286u, "User File"},
    {0x02004257u, "User Gamma"},
    {0x020023c2u, "Custom"},
};
/* Edit User Menu is the editor page for User Menu Item, so its rows are the add/remove actions
 * plus the pool of items that can be inserted. Only four of these action labels exist verbatim in
 * the containers; 'Delete Item' and 'Replace Item' are NOT present and are deliberately omitted
 * rather than invented. */
static const fx6_opt_t fx6_edit_user_items[] = {
    {0x02004d4bu, "Add Item"},
    {0x02004294u, "User Menu Item"},
    {0x02004d4au, "Edit User Menu"},
    {0x02004286u, "User File"},
    {0x02004264u, "Assignable Button"},
};

/* ----------------------------------------------------------------------
 * 3rd-layer option families for Project / Monitoring / TC-Media / Maintenance
 * ---------------------------------------------------------------------- */

/* Rec Format resolutions (ns2). The container repeats the same nine strings in several blocks,
 * because each recording mode has its own legal set; 0x4987..0x4990 is the first complete block. */
static const fx6_opt_t fx6_opt_rec_format[] = {
    {0x02004987u, "XAVC 4096×2160 P"},
    {0x02004989u, "XAVC 3840×2160 P"},
    {0x0200498bu, "XAVC 2048×1080 P"},
    {0x0200498du, "XAVC 1920×1080 P"},
    {0x0200498fu, "MPEG 1920×1080 i"},
};
/* Short alias forms stored alongside (0x4988 '4K', 0x498a 'QFHD', ...) */
static const fx6_opt_t fx6_opt_rec_format_short[] = {
    {0x02004988u, "4K"},    {0x0200498au, "QFHD"},  {0x0200498cu, "2K"},
    {0x0200498eu, "HD"},    {0x02004990u, "MPEGHD"},
};

/* Timecode family (ns2 0x48a5..0x48be) — the real ordered block for TC options. */
static const fx6_opt_t fx6_opt_timecode_mode[] = {
    {0x020048a5u, "Preset"},   {0x020048a7u, "Regen"},   {0x020048a9u, "Clock"},
    {0x020048abu, "Rec Run"},  {0x020048adu, "Free Run"},{0x020048afu, "Generator"},
};
static const fx6_opt_t fx6_opt_timecode_df[] = {
    {0x020048b1u, "DF"},  {0x020048b3u, "NDF"},
};
static const fx6_opt_t fx6_opt_timecode_src[] = {
    {0x020048b5u, "Fix"}, {0x020048b7u, "Time"}, {0x020048bbu, "Counter"}, {0x020048bdu, "Duration"},
};
static const fx6_opt_t fx6_opt_tc_out[] = {
    {0x0200456bu, "TC Out"}, {0x0200456du, "TC Format"}, {0x0200456fu, "Display Select"},
    {0x02004559u, "Timecode Lock"},
};

/* Monitoring display options (ns2 0x49e0..0x49ff). */
static const fx6_opt_t fx6_opt_monitor_display[] = {
    {0x020049ecu, "Marker"},  {0x020049edu, "Zebra"},   {0x020049f1u, "Peaking"},
    {0x020049f2u, "Display"}, {0x020049f4u, "Video Sig"}, {0x020049f5u, "Focus Magnifier"},
    {0x020049f7u, "VF Mode"}, {0x020049f9u, "ATW"},     {0x020049fbu, "ATW Hold"},
};
/* Audio source / format options (ns2 0x49e2..0x49eb). */
static const fx6_opt_t fx6_opt_audio_format[] = {
    {0x020049e2u, "Linear PCM"}, {0x020049e4u, "Dolby Digital"},
    {0x020049e6u, "Internal"},   {0x020049e8u, "External(HD)"},
    {0x020049eau, "External(SD)"},
};
/* Maintenance -> Language has NO ResID option table, and deliberately so: the language list is not
 * data. global.xdb registers one container per language (string_<lang>.uxc plus its _2 sibling), and
 * switching language is ResourceManager::switchBank(namespace), which swaps the whole string bank.
 * A per-row ResID array would therefore be wrong to fabricate. The neighbouring rows that DO have
 * option data are Country (0x0200426d) and Clock Set (0x0200426c). */

/* ======================================================================
 * PHASE 13 — sub-pages after the page breaks
 * ====================================================================== */

/* TABLE 0x2ea02f8 rows [36..46]: the second page of the three-layer menu (a 2-column layout with
 * a left grid list and a right stack of ten touch buttons, no 3rd column). */
static const fx6_menu_row_t fx6_three_layer_page2_rows[] = {
    {"No69_TOUCH_SCREEN",    0x042d5970u, {  0,  0,1024,540}, 0x00000000u, 0},
    {"No1_Backgroundleft",   0x042d5a40u, { 56, 49, 482,477}, 0x0200c006u, 0},
    {"No21_Backgroundright", 0x042d5a40u, {542, 49, 426,477}, 0x0200c006u, 0},
    {"No58_Gridlist",        0x042d59e0u, {126,102, 403,415}, 0x00000000u, 1},
    {"No68_itemtouchbutton10",0x042d58d0u,{546,493, 418, 44}, 0x00000000u, 2},
    {"No67_itemtouchbutton9", 0x042d58d0u,{546,449, 418, 44}, 0x00000000u, 2},
    {"No66_itemtouchbutton8", 0x042d58d0u,{546,405, 418, 44}, 0x00000000u, 2},
    {"No65_itemtouchbutton7", 0x042d58d0u,{546,361, 418, 44}, 0x00000000u, 2},
    {"No64_itemtouchbutton6", 0x042d58d0u,{546,317, 418, 44}, 0x00000000u, 2},
    {"No63_itemtouchbutton5", 0x042d58d0u,{546,273, 418, 44}, 0x00000000u, 2},
    {"No62_itemtouchbutton4", 0x042d58d0u,{546,229, 418, 44}, 0x00000000u, 2},
};
#define FX6_THREE_LAYER_PAGE2_COUNT \
    (sizeof(fx6_three_layer_page2_rows)/sizeof(fx6_three_layer_page2_rows[0]))

/* TABLE 0x2ea3e50 dialogs after the page break at row [10].
 *   [11..16]  Bluetooth Pairing dialog   (six rows up to the break at [17])
 *   [18..22]  File Transfer progress page (break at [23])
 *   [24..26]  toast / notification bar    (break at [27])
 *   [28]      full-screen touch catcher
 * Titles below were resolved from their desc+0x18 values, so they are the real strings. */
static const fx6_menu_row_t fx6_setting_dialog_rows[] = {
    {"No2_BG",          0x042d5a50u, { 56, 49,912,477}, 0x020001d2u, 0},  /* Bluetooth Pairing bg */
    {"No6_TEXT_1",      0x042d57f0u, { 72,108,884,256}, 0x02002b83u, 0},  /* pairing instructions */
    {"No1_TITLE",       0x042d57f0u, { 62, 54,894, 36}, 0x02002b77u, 0},  /* 'Bluetooth Pairing'  */
    {"No7_TEXT_2",      0x042d57f0u, { 72,409,884, 36}, 0x02002b9cu, 0},  /* 'Device Name: ...'   */
    {"No4_BUTTON_2",    0x042d58d0u, {774,463,182, 52}, 0x02004c46u, 0},  /* 'OK'                 */
    {"No3_BUTTON_1",    0x042d58d0u, {588,463,182, 52}, 0x020056e8u, 0},  /* 'Cancel'             */
    {"No1_TRANS_BG",    0x042d5a40u, {  0,  0,1024,540}, 0x0200c001u, 0}, /* transfer page bg     */
    {"No2_TITLE",       0x042d57f0u, {102, 80,820, 44}, 0x02005295u, 0},  /* 'File Transfer Mode' */
    {"No3_TRANSFERING", 0x042d57f0u, {232,232,560, 36}, 0x02005296u, 0},  /* 'File Transfering...'*/
    {"No4_PROGRESS_BAR",0x042d58b0u, {238,274,548, 22}, 0x00000000u, 0},
    {"No5_CANCEL",      0x042d58d0u, {740,456,182, 52}, 0x020056e8u, 0},  /* 'Cancel'             */
    {"No2_BG",          0x042d5a50u, {334, 47,354, 36}, 0x0200022fu, 0},  /* toast bg             */
    {"No3_TEXT",        0x042d57f0u, {368, 50,318, 30}, 0x00000000u, 0},  /* toast text (dynamic) */
    {"No4_ICON",        0x042d5a50u, {337, 51, 28, 28}, 0x0200022eu, 0},  /* toast icon           */
    {"No11_touchscreen",0x042d5970u, {  0,  0,1024,540}, 0x00000000u, 0},
};
#define FX6_SETTING_DIALOG_COUNT \
    (sizeof(fx6_setting_dialog_rows)/sizeof(fx6_setting_dialog_rows[0]))

/* Extended category map: now all eleven categories are covered. */
static const fx6_category_map_t fx6_category_map_full[] = {
    FX6_CATMAP_ENTRY(0x02004208u, fx6_user_items),          /* User          */
    FX6_CATMAP_ENTRY(0x02004d4au, fx6_edit_user_items),     /* Edit User Menu*/
    FX6_CATMAP_ENTRY(0x02002227u, fx6_shooting_items),      /* Shooting      */
    FX6_CATMAP_ENTRY(0x02002228u, fx6_project_items),       /* Project       */
    FX6_CATMAP_ENTRY(0x02002493u, fx6_paint_items),         /* Paint/Look    */
    FX6_CATMAP_ENTRY(0x0200222bu, fx6_tc_media_items),      /* TC/Media      */
    FX6_CATMAP_ENTRY(0x02002229u, fx6_monitoring_items),    /* Monitoring    */
    FX6_CATMAP_ENTRY(0x020041fbu, fx6_audio_items),         /* Audio         */
    FX6_CATMAP_ENTRY(0x02004209u, fx6_thumbnail_items),     /* Thumbnail     */
    FX6_CATMAP_ENTRY(0x0200222au, fx6_technical_items),     /* Technical     */
    FX6_CATMAP_ENTRY(0x02004203u, fx6_maintenance_items),   /* Maintenance   */
};
#define FX6_CATEGORY_MAP_FULL_COUNT \
    (sizeof(fx6_category_map_full)/sizeof(fx6_category_map_full[0]))

/* ======================================================================
 * PHASE 14 — every 0x48 descriptor region in appFw.so
 * ======================================================================
 * A full sweep of .rodata and .data.rel.ro for maximal runs of rows whose +0x00 is one of the
 * known view tags yields 23 regions / 2316 rows. The four already-documented tables are inside
 * these regions (0x2e9e210 sits in the 0x2e9d9e8 region, 0x2ea3e50 and 0x2ea02f8 in 0x2e9e528,
 * 0x2eaf208 in 0x2ea5878), because adjacent pages butt against each other with no padding.
 *
 * So the list below is a *region* index, not a page index: a region can hold several pages, and
 * page boundaries inside a region are marked by tag 0x42d5a60 (all-zero rect). Use
 * FX6_IS_PAGE_BREAK() to split them.
 */
typedef struct {
    uint32_t base;
    uint16_t rows;
    uint16_t tag_mix;      /* number of distinct class tags inside the region */
    const char *first_name;
} fx6_desc_region_t;

static const fx6_desc_region_t fx6_desc_regions[] = {
    {0x02e91040u,   5, 2, "No18_clip_name"},
    {0x02e911f0u,   8, 2, "No2011_audio_level_meter"},
    {0x02e91508u,   3, 1, "No8_codec"},
    {0x02e91628u,   5, 1, "No6_picture_size"},
    {0x02e917d8u, 175, 3, "No2010_gamma_display_assist"},
    {0x02e94c28u,  40, 2, "No133_homemenu_clip_area"},
    {0x02e957b0u,   5, 2, "No2045_video_signal_monitor"},
    {0x02e959a8u,   7, 2, "No1066_base_look"},
    {0x02e95cc0u,   8, 3, "No2094_tracking_cancel_button"},
    {0x02e95f90u,  10, 3, "No76_base_look"},
    {0x02e962a8u,   8, 3, "No16_resolution"},
    {0x02e96608u,  11, 3, "No4_recstate_string_slot_1st"},
    {0x02e96a40u,   3, 2, "No27_rec_function"},
    {0x02e96bf0u, 237, 3, "No6_stbystate_slot_2nd"},
    {0x02e9afb8u,  29, 3, "No40_CONTENT_NUMBER"},
    {0x02e9b828u,  21, 3, "No30_clip_footer"},
    {0x02e9be58u,  97, 3, "No37_duration"},
    {0x02e9d9e8u,  33, 3, "No48_digital_signature_cr_icon"},
    {0x02e9e378u,   5, 1, "No2071_TIME_CODE_VALUE"},
    {0x02e9e528u, 409, 3, "No1172_SHOT_OR_CLIP_NUMBER_VALUE"},
    {0x02ea5878u, 964, 3, "No4_BLOCK_TOUCH"},
    {0x02eb67e0u,   4, 3, "No2_TITLE_BG"},
    {0x02eb6948u, 229, 3, "No12_SET_BUTTON"},
};
#define FX6_DESC_REGION_COUNT (sizeof(fx6_desc_regions)/sizeof(fx6_desc_regions[0]))

/* The largest regions are the interesting ones for new UI:
 *   0x2ea5878 (964)  every full-screen setting page, separated by 0x42d5a60 breaks
 *   0x2e9e528 (409)  home presenter pages
 *   0x2e96bf0 (237)  standby / viewfinder OSD state pages
 *   0x2eb6948 (229)  SET-button pages (26 page breaks inside)
 *   0x2e917d8 (175)  on-screen overlay / gamma-display-assist layer
 */

/* ----------------------------------------------------------------------
 * New page: audio level meter + status strip  (region 0x2e911f0, 8 rows)
 * The two meter widgets are 58x112 at x=931, i.e. the right edge of the frame.
 * ---------------------------------------------------------------------- */
static const fx6_menu_row_t fx6_audio_meter_rows[] = {
    /* base 0x02e911f0, 8 rows */
    {"No2011_audio_level_meter", 0x042d57d0u, {931,391,58,112}, 0x00000000u, 0},
    {"No1005_audio_level_meter", 0x042d57d0u, {931,394,58,112}, 0x00000000u, 0},
    {"No1001_content_number", 0x042d57f0u, {96,5,206,30}, 0x00000000u, 0},
    {"No2022_tcub", 0x042d57d0u, {34,505,180,32}, 0x00000000u, 0},
    {"No2017_clip_name", 0x042d57f0u, {464,507,196,28}, 0x020050c4u, 0},
    {"No9_baselook", 0x042d57f0u, {823,199,165,32}, 0x02004b37u, 0},
    {"No17_play_string", 0x042d57f0u, {508,6,144,36}, 0x020050d1u, 0},
    {"No1010_play_string", 0x042d57f0u, {522,2,144,36}, 0x020050d1u, 0},
};
#define FX6_AUDIO_METER_ROWS_COUNT (sizeof(fx6_audio_meter_rows)/sizeof(fx6_audio_meter_rows[0]))

static const fx6_menu_row_t fx6_clip_footer_rows[] = {
    /* base 0x02e9b828, 21 rows */
    {"No30_clip_footer", 0x042d5a50u, {0,460,1024,80}, 0x02000311u, 0},
    {"No1_clip_header", 0x042d5a50u, {0,0,1024,52}, 0x02000312u, 0},
    {"No4_option_bg", 0x042d5a50u, {38,0,534,54}, 0x0200032bu, 0},
    {"No21_clip_thumbnail", 0x042d58f0u, {746,325,203,132}, 0x00000000u, 0},
    {"No20_clip_thumbnail", 0x042d58f0u, {522,325,203,132}, 0x00000000u, 0},
    {"No19_clip_thumbnail", 0x042d58f0u, {298,325,203,132}, 0x00000000u, 0},
    {"No18_clip_thumbnail", 0x042d58f0u, {74,325,203,132}, 0x00000000u, 0},
    {"No17_clip_thumbnail", 0x042d58f0u, {746,190,203,132}, 0x00000000u, 0},
    {"No16_clip_thumbnail", 0x042d58f0u, {522,190,203,132}, 0x00000000u, 0},
    {"No15_clip_thumbnail", 0x042d58f0u, {298,190,203,132}, 0x00000000u, 0},
    {"No14_clip_thumbnail", 0x042d58f0u, {74,190,203,132}, 0x00000000u, 0},
    {"No13_clip_thumbnail", 0x042d58f0u, {746,55,203,132}, 0x00000000u, 0},
    {"No12_clip_thumbnail", 0x042d58f0u, {522,55,203,132}, 0x00000000u, 0},
    {"No11_clip_thumbnail", 0x042d58f0u, {298,55,203,132}, 0x00000000u, 0},
    {"No10_clip_thumbnail", 0x042d58f0u, {74,55,203,132}, 0x00000000u, 0},
    {"No31_clip_name", 0x042d57f0u, {57,464,536,30}, 0x00000000u, 0},
    {"No3_clip_title", 0x042d57f0u, {99,12,302,36}, 0x02005209u, 0},
    {"No36_criate_time", 0x042d5840u, {675,464,292,30}, 0x00000000u, 0},
    {"No6_option_exec_guide", 0x042d57f0u, {308,13,246,30}, 0x02004fe2u, 0},
    {"No5_option_title", 0x042d57f0u, {56,13,246,30}, 0x00000000u, 0},
    {"No35_rec_mode", 0x042d57f0u, {520,496,242,30}, 0x00000000u, 0},
};
#define FX6_CLIP_FOOTER_ROWS_COUNT (sizeof(fx6_clip_footer_rows)/sizeof(fx6_clip_footer_rows[0]))

static const fx6_menu_row_t fx6_confirm_dialog_rows[] = {
    /* base 0x02eb67e0, 4 rows */
    {"No2_TITLE_BG", 0x042d5a50u, {0,47,592,38}, 0x02000210u, 0},
    {"No3_TITLE", 0x042d57f0u, {57,48,502,36}, 0x00000000u, 0},
    {"No13_GUIDE", 0x042d57f0u, {521,416,450,36}, 0x02002ad1u, 0},
    {"No6_VALUE_BUTTON", 0x042d58d0u, {57,100,196,58}, 0x00000000u, 0},
};
#define FX6_CONFIRM_DIALOG_ROWS_COUNT (sizeof(fx6_confirm_dialog_rows)/sizeof(fx6_confirm_dialog_rows[0]))

static const fx6_menu_row_t fx6_content_number_rows[] = {
    /* base 0x02e9afb8, 29 rows */
    {"No40_CONTENT_NUMBER", 0x042d57f0u, {248,298,150,32}, 0x00000000u, 0},
    {"No122_PLAYBACK_STATUS_STRING", 0x042d57f0u, {227,256,126,32}, 0x020050d1u, 0},
    {"No422_SQ_FRAME_RATE", 0x042d57f0u, {663,298,98,32}, 0x00000000u, 0},
    {"No421_INT_REC_STATUS", 0x042d57f0u, {663,298,98,32}, 0x00000000u, 0},
    {"No34_SEPARATOR", 0x042d5a40u, {96,382,768,4}, 0x0200c00eu, 0},
    {"No33_SEPARATOR", 0x042d5a40u, {96,190,768,4}, 0x0200c00eu, 0},
    {"No15_RESOLUTION", 0x042d57f0u, {677,342,84,32}, 0x02002999u, 0},
    {"No10_ERROR_CODE", 0x042d57f0u, {99,279,52,38}, 0xffffffffu, 0},
    {"No7_TIME_DATA_TYPE", 0x042d5a50u, {104,204,44,40}, 0x00000000u, 0},
    {"No121_PLAYBACK_STATUS_ICON", 0x042d57f0u, {180,256,47,32}, 0x0200283cu, 0},
    {"No8_FRAME_RATE_UNIT", 0x042d57f0u, {514,213,42,32}, 0x0200532du, 0},
    {"No8_FRAME_RATE_VALUE_DECIMAL", 0x042d57f0u, {472,213,40,32}, 0xffffffffu, 0},
    {"No8_FRAME_RATE_VALUE_INTEGER", 0x042d57f0u, {440,213,34,32}, 0xffffffffu, 0},
    {"No202_MEDIA_PROTECT_SLOT", 0x042d5a50u, {214,297,32,34}, 0x00000000u, 0},
    {"No201_MEDIA_SLOT", 0x042d57f0u, {180,297,32,34}, 0x02002822u, 0},
    {"No10_ERROR_WARNING_ICON", 0x042d5a50u, {112,281,28,28}, 0x00000000u, 0},
    {"No32_SEPARATOR", 0x042d5a40u, {607,386,4,118}, 0x0200c00eu, 0},
    {"No31_SEPARATOR", 0x042d5a40u, {349,386,4,118}, 0x0200c00eu, 0},
    {"No30_SEPARATOR", 0x042d5a40u, {607,72,4,118}, 0x0200c00eu, 0},
    {"No29_SEPARATOR", 0x042d5a40u, {349,72,4,118}, 0x0200c00eu, 0},
    {"No105_BUTTON_05", 0x042d58d0u, {349,382,262,122}, 0x00000000u, 0},
    {"No102_BUTTON_02", 0x042d58d0u, {349,72,262,122}, 0x00000000u, 0},
    {"No106_BUTTON_06", 0x042d58d0u, {607,382,257,122}, 0x00000000u, 0},
    {"No104_BUTTON_04", 0x042d58d0u, {96,382,257,122}, 0x00000000u, 0},
    {"No103_BUTTON_03", 0x042d58d0u, {607,72,257,122}, 0x00000000u, 0},
    {"No101_BUTTON_01", 0x042d58d0u, {96,72,257,122}, 0x00000000u, 0},
    {"No2_MESSAGE_REQUEST", 0x042d5920u, {0,0,1024,540}, 0x00000000u, 0},
    {"", 0x042d5a60u, {0,0,0,0}, 0x00000000u, 0},
    {"No44_yuv_cover", 0x042d5a40u, {0,0,1024,540}, 0x0200c001u, 0},
};
#define FX6_CONTENT_NUMBER_ROWS_COUNT (sizeof(fx6_content_number_rows)/sizeof(fx6_content_number_rows[0]))

static const fx6_menu_row_t fx6_homemenu_clip_rows[] = {
    /* base 0x02e94c28, 40 rows */
    {"No133_homemenu_clip_area", 0x042d57d0u, {96,72,768,432}, 0x00000000u, 0},
    {"No1116_upper_homemenu_clip_area", 0x042d57d0u, {32,0,960,70}, 0x00000000u, 0},
    {"No96_direct_menu_list_shutter_mode", 0x042d5a40u, {464,390,320,150}, 0x0200c001u, 0},
    {"No2102_direct_menu_list_shutter_mode", 0x042d5a40u, {260,3,320,150}, 0x0200c001u, 0},
    {"No1078_direct_menu_list_shutter_mode", 0x042d5a40u, {618,390,320,150}, 0x0200c001u, 0},
    {"No2097_direct_menu_list_focus_mode", 0x042d5a40u, {32,3,310,150}, 0x0200c001u, 0},
    {"No1115_upper_fullmenu_clip_area", 0x042d57d0u, {32,0,960,46}, 0x00000000u, 0},
    {"No97_direct_menu_list_exposure_mode", 0x042d5a40u, {659,390,300,150}, 0x0200c001u, 0},
    {"No95_direct_menu_list_gain_mode", 0x042d5a40u, {480,390,300,150}, 0x0200c001u, 0},
    {"No94_direct_menu_list_iris_mode", 0x042d5a40u, {388,390,300,150}, 0x0200c001u, 0},
    {"No93_direct_menu_list_nd_filter_mode", 0x042d5a40u, {252,390,300,150}, 0x0200c001u, 0},
    {"No92_direct_menu_list_scene_file", 0x042d5a40u, {274,390,300,150}, 0x0200c001u, 0},
    {"No89_direct_menu_list_focus_mode", 0x042d5a40u, {32,47,300,150}, 0x0200c001u, 0},
    {"No86_direct_menu_list_white_mode", 0x042d5a40u, {32,343,300,150}, 0x0200c001u, 0},
    {"No85_direct_menu_list_steady_shot", 0x042d5a40u, {32,161,300,150}, 0x0200c001u, 0},
    {"No2199_direct_menu_list_nd_filter_mode", 0x042d5a40u, {146,390,300,150}, 0x0200c001u, 0},
    {"No2104_direct_menu_list_base_iso", 0x042d5a40u, {34,112,300,150}, 0x0200c001u, 0},
    {"No2103_direct_menu_list_exposure_mode", 0x042d5a40u, {564,44,300,150}, 0x0200c001u, 0},
    {"No2101_direct_menu_list_gain_mode", 0x042d5a40u, {532,3,300,150}, 0x0200c001u, 0},
    {"No2100_direct_menu_list_iris_mode", 0x042d5a40u, {371,3,300,150}, 0x0200c001u, 0},
    {"No2098_direct_menu_list_scene_file", 0x042d5a40u, {34,268,300,150}, 0x0200c001u, 0},
    {"No2096_direct_menu_list_white_mode", 0x042d5a40u, {698,3,300,150}, 0x0200c001u, 0},
    {"No2095_direct_menu_list_steady_shot", 0x042d5a40u, {833,277,300,150}, 0x0200c001u, 0},
    {"No1114_direct_menu_list_base_iso", 0x042d5a40u, {424,390,300,150}, 0x0200c001u, 0},
    {"No1079_direct_menu_list_exposure_mode", 0x042d5a40u, {32,390,300,150}, 0x0200c001u, 0},
    {"No1077_direct_menu_list_gain_mode", 0x042d5a40u, {96,390,300,150}, 0x0200c001u, 0},
    {"No1076_direct_menu_list_iris_mode", 0x042d5a40u, {274,390,300,150}, 0x0200c001u, 0},
    {"No1075_direct_menu_list_nd_filter_mode", 0x042d5a40u, {140,390,300,150}, 0x0200c001u, 0},
    {"No1074_direct_menu_list_scene_file", 0x042d5a40u, {750,171,300,150}, 0x0200c001u, 0},
    {"No1072_direct_menu_list_focus_mode", 0x042d5a40u, {32,3,300,150}, 0x0200c001u, 0},
    {"No1071_direct_menu_list_white_mode", 0x042d5a40u, {710,390,300,150}, 0x0200c001u, 0},
    {"No1070_direct_menu_list_steady_shot", 0x042d5a40u, {32,165,300,150}, 0x0200c001u, 0},
    {"No2201_bottom_homemenu_clip_area", 0x042d57d0u, {32,504,960,36}, 0x00000000u, 0},
    {"No2200_upper_homemenu_clip_area", 0x042d57d0u, {32,0,960,36}, 0x00000000u, 0},
    {"No1119_right_homemenu_clip_area", 0x042d57d0u, {876,34,114,290}, 0x00000000u, 0},
    {"No1117_bottom_homemenu_clip_area", 0x042d57d0u, {32,507,960,33}, 0x00000000u, 0},
    {"No90_direct_menu_list_sq_frame_rate", 0x042d5a40u, {686,82,200,150}, 0x0200c001u, 0},
    {"No1073_direct_menu_list_sq_frame_rate", 0x042d5a40u, {792,66,200,150}, 0x0200c001u, 0},
    {"No2202_left_homemenu_clip_area", 0x042d57d0u, {32,36,64,468}, 0x00000000u, 0},
    {"No1118_left_homemenu_clip_area", 0x042d57d0u, {32,49,64,458}, 0x00000000u, 0},
};
#define FX6_HOMEMENU_CLIP_ROWS_COUNT (sizeof(fx6_homemenu_clip_rows)/sizeof(fx6_homemenu_clip_rows[0]))


/* ----------------------------------------------------------------------
 * Clip / thumbnail grid pages
 * ----------------------------------------------------------------------
 * fx6_clip_footer_rows shows the real thumbnail grid: 12 cells of 203x132 in a 4x3 layout,
 *   x = 74, 298, 522, 746      (pitch 224)
 *   y = 55, 190, 325           (pitch 135)
 * plus a full-width footer (0,460,1024,80) and header (0,0,1024,52).
 * Those pitches are the concrete numbers a thumbnail page needs; they are not derivable from any
 * single descriptor, only from the set.
 */
#define FX6_THUMB_COLS      4
#define FX6_THUMB_ROWS      3
#define FX6_THUMB_W         203
#define FX6_THUMB_H         132
#define FX6_THUMB_X0        74
#define FX6_THUMB_Y0        55
#define FX6_THUMB_DX        224
#define FX6_THUMB_DY        135
#define FX6_CLIP_FOOTER_RECT  {0,460,1024,80}
#define FX6_CLIP_HEADER_RECT  {0,0,1024,52}

/* ======================================================================
 * PHASE 15 — the full page directory
 * ======================================================================
 * Every 0x48 descriptor region was split at tag 0x042d5a60 with an all-zero rect. The complete
 * descriptor space is **10 regions / 2345 rows / 128 pages**.
 *
 * IMPORTANT CORRECTION to round 682: the region count there was 23 / 2316 rows only because the
 * tag filter was incomplete (25 distinct class tags are in use, not 18). With all 25 tags the
 * regions merge into 10, and two of the "regions" reported earlier — 0x2ea5878 (964 rows) and
 * 0x2eb6948 (229 rows) — are NOT region bases at all: they are ordinary rows inside one big region
 * that starts at 0x2e96e50 and spans 2061 rows. Both were page boundaries in the old listing purely
 * as an artefact of the truncated tag set.
 *
 * Sanity check against independently measured tables:
 *   0x2e9e210 -> page 21, 98 rows   (matches the home-presenter count)
 *   0x2ea02f8 -> page 24, 35 rows   (the three-layer page 1, before its break)
 *   0x2ea3e50 -> page 36, 10 rows   (Setting main)
 *   0x2eaf208 -> page 80, 17 rows   (Setting centre)
 */
typedef struct {
    uint16_t page_index;
    uint8_t  region_index;
    uint32_t base_va;
    uint16_t row_count;
    uint16_t str_count;
    uint16_t fill_count;
    uint16_t icon_count;
    uint16_t menu_item_count;
    const char *first_name;
} fx6_page_dir_t;

static const fx6_page_dir_t fx6_all_pages[] = {
    {  0,  0, 0x02e90fb0u,   7,  4,  0,  0,  0, "No33_touch"},
    {  1,  1, 0x02e911f0u,  14,  8,  0,  0,  0, "No2011_audio_level_meter"},
    {  2,  2, 0x02e91628u,   5,  5,  0,  0,  0, "No6_picture_size"},
    {  3,  3, 0x02e917d8u,  71, 15,  0, 41,  0, "No2010_gamma_display_assist"},
    {  4,  3, 0x02e92c18u, 102, 31, 29,  3, 37, "No142_BLOCK_TOUCH"},
    {  5,  4, 0x02e94c28u,  40,  0, 31,  0,  0, "No133_homemenu_clip_area"},
    {  6,  5, 0x02e957b0u,   5,  1,  0,  0,  0, "No2045_video_signal_monitor"},
    {  7,  6, 0x02e959a8u,   7,  6,  0,  0,  0, "No1066_base_look"},
    {  8,  7, 0x02e95cc0u,  20,  8,  0,  1,  0, "No2094_tracking_cancel_button"},
    {  9,  8, 0x02e962a8u,  11,  3,  0,  0,  0, "No16_resolution"},
    { 10,  9, 0x02e96608u, 253, 78,  0, 125,  0, "No4_recstate_string_slot_1st"},
    { 11,  9, 0x02e9ad78u,  35, 14,  8,  3,  6, "No423_BLOCK_TOUCH"},
    { 12,  9, 0x02e9b798u,  39, 11,  3,  9,  0, "No44_yuv_cover"},
    { 13,  9, 0x02e9c2d8u,   6,  2,  0,  2,  0, "No3_BG_MENU"},
    { 14,  9, 0x02e9c4d0u,   4,  2,  0,  1,  0, "No2_BG"},
    { 15,  9, 0x02e9c638u,   4,  3,  0,  1,  0, "No2_BG"},
    { 16,  9, 0x02e9c7a0u,   3,  1,  1,  1,  0, "No1_BG"},
    { 17,  9, 0x02e9c8c0u,  20, 14,  6,  0,  0, "No1_TRANS_BG"},
    { 18,  9, 0x02e9cef0u,  46, 25,  1,  7,  3, "No43_yuv_cover"},
    { 19,  9, 0x02e9dc28u,   8,  4,  1,  1,  1, "No8_BLOCK_TOUCH"},
    { 20,  9, 0x02e9deb0u,  11,  6,  0,  2,  0, "No17_TOUCH_SCREEN"},
    { 21,  9, 0x02e9e210u,  98, 56,  8, 20,  6, "No463_BLOCK_TOUCH"},
    { 22,  9, 0x02e9fde8u,   3,  1,  0,  0,  0, "No2_enlargeareadebugdisplay"},
    { 23,  9, 0x02e9ff08u,  13,  4,  1,  2,  1, "No16_TOUCH_SCREEN"},
    { 24,  9, 0x02ea02f8u,  35, 10, 15,  1,  8, "No1_WID_NINEPATCHIMAGE_STAGE1_BG"},
    { 25,  9, 0x02ea0d18u,  69, 24, 23,  2, 18, "No69_TOUCH_SCREEN"},
    { 26,  9, 0x02ea20c8u,  23,  3, 13,  4,  1, "No23_TOUCH_SCREEN"},
    { 27,  9, 0x02ea2788u,  23,  3, 13,  4,  1, "No33_TOUCH_SCREEN"},
    { 28,  9, 0x02ea2e48u,  16,  6,  0,  2,  7, "No20_TOUCH"},
    { 29,  9, 0x02ea3310u,  14,  4,  0,  2,  7, "No20_TOUCH"},
    { 30,  9, 0x02ea3748u,   1,  0,  1,  0,  0, "No1_BG"},
    { 31,  9, 0x02ea37d8u,  10,  5,  0,  2,  0, "No18_TOUCH_SCREEN"},
    { 32,  9, 0x02ea3af0u,   3,  1,  0,  1,  0, "No2_BG"},
    { 33,  9, 0x02ea3c10u,   2,  1,  0,  1,  0, "No2_BG"},
    { 34,  9, 0x02ea3ce8u,   2,  1,  0,  1,  0, "No2_BG"},
    { 35,  9, 0x02ea3dc0u,   1,  0,  1,  0,  0, "No1_BG"},
    { 36,  9, 0x02ea3e50u,  10,  4,  0,  0,  4, "No107_BLOCK_TOUCH"},
    { 37,  9, 0x02ea4168u,   6,  3,  0,  1,  2, "No2_BG"},
    { 38,  9, 0x02ea4360u,   5,  2,  1,  0,  1, "No1_TRANS_BG"},
    { 39,  9, 0x02ea4510u,   3,  1,  0,  2,  0, "No2_BG"},
    { 40,  9, 0x02ea4630u,  11,  0,  3,  6,  0, "No11_touchscreen"},
    { 41,  9, 0x02ea4990u,  33,  5,  8,  1, 18, "No26_TOUCH_SCREEN"},
    { 42,  9, 0x02ea5320u,   7,  4,  0,  2,  1, "No2_BG"},
    { 43,  9, 0x02ea5560u,  11,  4,  2,  1,  1, "No19_TOUCH_SCREEN"},
    { 44,  9, 0x02ea58c0u,   4,  1,  0,  1,  1, "No4_BLOCK_TOUCH"},
    { 45,  9, 0x02ea5a28u,   5,  1,  0,  1,  2, "No5_BLOCK_TOUCH"},
    { 46,  9, 0x02ea5bd8u,   5,  2,  0,  1,  1, "No6_BLOCK_TOUCH"},
    { 47,  9, 0x02ea5d88u,   6,  2,  0,  1,  2, "No7_BLOCK_TOUCH"},
    { 48,  9, 0x02ea5f80u,   7,  4,  0,  1,  1, "No7_BLOCK_TOUCH"},
    { 49,  9, 0x02ea61c0u,   7,  3,  0,  1,  2, "No8_BLOCK_TOUCH"},
    { 50,  9, 0x02ea6400u,  11,  1,  0,  2,  7, "No19_TOUCH"},
    { 51,  9, 0x02ea6760u,  12,  1,  0,  2,  8, "No17_TOUCH"},
    { 52,  9, 0x02ea6b08u,  19,  8,  0,  2,  8, "No26_TOUCH"},
    { 53,  9, 0x02ea70a8u,  13,  1,  0,  2,  9, "No19_TOUCH"},
    { 54,  9, 0x02ea7498u,   1,  0,  1,  0,  0, "No1_BG"},
    { 55,  9, 0x02ea7528u,   3,  2,  0,  0,  0, "No3_touch_screen"},
    { 56,  9, 0x02ea7648u, 176, 11, 110, 25, 25, "No48_TOUCH_SCREEN"},
    { 57,  9, 0x02eaa810u,  18,  1,  6,  0, 10, "No18_TOUCH_SCREEN"},
    { 58,  9, 0x02eaad68u,  48, 22,  6,  7,  6, "No59_TOUCH_SCREEN"},
    { 59,  9, 0x02eabb30u,   3,  1,  0,  1,  0, "No2_BG"},
    { 60,  9, 0x02eabc50u,   4,  2,  0,  1,  0, "No2_EXECUTING_MESSAGE_BG"},
    { 61,  9, 0x02eabdb8u,   7,  4,  0,  3,  0, "No4_BG_2LINE"},
    { 62,  9, 0x02eabff8u,   1,  0,  1,  0,  0, "No1_BG"},
    { 63,  9, 0x02eac088u,   6,  0,  0,  1,  3, "No6_TOUCH_SCREEN"},
    { 64,  9, 0x02eac280u,  34,  6,  8,  1, 18, "No26_TOUCH_SCREEN"},
    { 65,  9, 0x02eacc58u,   4,  1,  0,  1,  1, "No1_BG"},
    { 66,  9, 0x02eacdc0u,  10,  4,  2,  1,  1, "No12_TOUCH_SCREEN"},
    { 67,  9, 0x02ead0d8u,  26,  6,  7,  1, 11, "No25_TOUCH_SCREEN"},
    { 68,  9, 0x02ead870u,  55, 28,  6,  1, 15, "No48_TOUCH_SCREEN"},
    { 69,  9, 0x02eae830u,  34,  6,  8,  1, 18, "No26_TOUCH_SCREEN"},
    { 70,  9, 0x02eaf208u,  17,  2,  8,  0,  6, "No107_BLOCK_TOUCH"},
    { 71,  9, 0x02eaf718u,   1,  0,  1,  0,  0, "No1_BG"},
    { 72,  9, 0x02eaf7a8u,  10,  5,  2,  0,  2, "No8_BLOCK_TOUCH"},
    { 73,  9, 0x02eafac0u,  10,  4,  2,  1,  1, "No10_TOUCH_SCREEN"},
    { 74,  9, 0x02eafdd8u,  49, 13, 22,  2, 10, "No49_TOUCH_SCREEN"},
    { 75,  9, 0x02eb0be8u,   3,  2,  0,  1,  0, "No2_BG"},
    { 76,  9, 0x02eb0d08u,  28,  6,  8,  1, 12, "No25_TOUCH_SCREEN"},
    { 77,  9, 0x02eb1530u,  11,  6,  2,  0,  1, "No13_TOUCH_SCREEN"},
    { 78,  9, 0x02eb1890u,  54, 21, 11,  6, 12, "No45_TOUCH_SCREEN"},
    { 79,  9, 0x02eb2808u,   9,  3,  1,  2,  1, "No7_TOUCH_SCREEN"},
    { 80,  9, 0x02eb2ad8u,   8,  2,  0,  3,  2, "No32_BG"},
    { 81,  9, 0x02eb2d60u,  10,  7,  0,  1,  2, "No8_BG"},
    { 82,  9, 0x02eb3078u,   4,  1,  0,  1,  1, "No6_BLOCK_TOUCH"},
    { 83,  9, 0x02eb31e0u,   5,  1,  0,  1,  2, "No6_BLOCK_TOUCH"},
    { 84,  9, 0x02eb3390u,   4,  1,  0,  1,  1, "No5_BLOCK_TOUCH"},
    { 85,  9, 0x02eb34f8u,   5,  1,  0,  1,  2, "No6_BLOCK_TOUCH"},
    { 86,  9, 0x02eb36a8u,  17, 11,  2,  1,  2, "No20_BG"},
    { 87,  9, 0x02eb3bb8u,   8,  3,  0,  2,  0, "No18_TOUCH_SCREEN"},
    { 88,  9, 0x02eb3e40u,   3,  1,  0,  1,  0, "No4_BG"},
    { 89,  9, 0x02eb3f60u,   3,  1,  0,  1,  0, "No2_NINEPATCHIMAGE_0"},
    { 90,  9, 0x02eb4080u,   8,  2,  0,  3,  1, "No7_TOUCH_SCREEN"},
    { 91,  9, 0x02eb4308u,   5,  3,  0,  1,  0, "No5_SETTING_LIST_BACKGROUND"},
    { 92,  9, 0x02eb44b8u,  19,  2,  2,  5,  9, "No30_TOUCH_SCREEN"},
    { 93,  9, 0x02eb4a58u,  12,  6,  0,  3,  2, "No11_BLOCK_TOUCH"},
    { 94,  9, 0x02eb4e00u,  19,  4,  0,  2, 12, "No30_TOUCH"},
    { 95,  9, 0x02eb53a0u,  28,  6,  8,  1, 12, "No25_TOUCH_SCREEN"},
    { 96,  9, 0x02eb5bc8u,   6,  2,  0,  1,  1, "No6_BLOCK_TOUCH"},
    { 97,  9, 0x02eb5dc0u,   7,  3,  0,  1,  1, "No12_BLOCK_TOUCH"},
    { 98,  9, 0x02eb6000u,   4,  2,  0,  1,  0, "No5_TOUCH"},
    { 99,  9, 0x02eb6168u,   5,  3,  0,  1,  0, "No9_TOUCH"},
    {100,  9, 0x02eb6318u,   6,  4,  0,  1,  0, "No6_TOUCH"},
    {101,  9, 0x02eb6510u,   7,  5,  0,  1,  0, "No7_TOUCH"},
    {102,  9, 0x02eb6750u,  10,  2,  0,  3,  2, "No9_TOUCH"},
    {103,  9, 0x02eb6a68u,   4,  2,  0,  1,  1, "No6_BG"},
    {104,  9, 0x02eb6bd0u,   4,  2,  0,  1,  0, "No1_BG"},
    {105,  9, 0x02eb6d38u,   5,  3,  0,  1,  1, "No1_BG"},
    {106,  9, 0x02eb6ee8u,   5,  1,  0,  1,  2, "No5_BLOCK_TOUCH"},
    {107,  9, 0x02eb7098u,   5,  2,  0,  1,  1, "No6_BLOCK_TOUCH"},
    {108,  9, 0x02eb7248u,   5,  2,  0,  1,  1, "No6_BLOCK_TOUCH"},
    {109,  9, 0x02eb73f8u,   6,  2,  0,  1,  2, "No7_BLOCK_TOUCH"},
    {110,  9, 0x02eb75f0u,  54,  6, 16,  1, 30, "No32_TOUCH_SCREEN"},
    {111,  9, 0x02eb8568u,   6,  1,  0,  0,  1, "No7_TOUCH_SCREEN_FOR_RELEASE"},
    {112,  9, 0x02eb8760u,  11,  6,  0,  2,  1, "No11_TOUCH_SCREEN"},
    {113,  9, 0x02eb8ac0u,   7,  0,  1,  1,  3, "No11_TOUCH_SCREEN"},
    {114,  9, 0x02eb8d00u,   3,  2,  0,  1,  0, "No1_BG"},
    {115,  9, 0x02eb8e20u,   9,  1,  0,  0,  5, "No8_TOUCH_SCREEN_FOR_RELEASE"},
    {116,  9, 0x02eb90f0u,  10,  4,  2,  1,  2, "No15_TOUCH_SCREEN"},
    {117,  9, 0x02eb9408u,   6,  3,  0,  1,  1, "No7_BLOCK_TOUCH"},
    {118,  9, 0x02eb9600u,   4,  2,  0,  1,  0, "No8_TOUCH"},
    {119,  9, 0x02eb9768u,   5,  3,  0,  1,  0, "No6_TOUCH"},
    {120,  9, 0x02eb9918u,   4,  2,  0,  1,  0, "No4_TOUCH"},
    {121,  9, 0x02eb9a80u,   6,  2,  0,  1,  1, "No6_BLOCK_TOUCH"},
    {122,  9, 0x02eb9c78u,   8,  1,  1,  1,  3, "No11_TOUCH_SCREEN"},
    {123,  9, 0x02eb9f00u,   5,  3,  0,  1,  0, "No5_TOUCH"},
    {124,  9, 0x02eba0b0u,   5,  3,  0,  1,  0, "No5_TOUCH"},
    {125,  9, 0x02eba260u,  10,  4,  2,  1,  1, "No11_TOUCH_SCREEN"},
    {126,  9, 0x02eba578u,   7,  0,  1,  0,  6, "No1_BG"},
    {127,  9, 0x02eba7b8u,   6,  0,  0,  0,  6, "No1_BUTTON_01"},
};
#define FX6_ALL_PAGES_COUNT (sizeof(fx6_all_pages)/sizeof(fx6_all_pages[0]))


/* Helper: iterate the directory looking for a page that contains `va`. */
static inline const fx6_page_dir_t *fx6_page_for_va(uint32_t va)
{
    for (unsigned i = 0; i < FX6_ALL_PAGES_COUNT; i++) {
        const fx6_page_dir_t *p = &fx6_all_pages[i];
        if (va >= p->base_va && va < p->base_va + (uint32_t)p->row_count * FX6_DESC_STRIDE)
            return p;
    }
    return 0;
}

/* Pages ranked by content, for picking a render target quickly. */
#define FX6_PAGE_HOME          21u   /* 0x02e9e210  98 rows  s56 f8  i20 m6  */
#define FX6_PAGE_THREE_LAYER   24u   /* 0x02ea02f8  35 rows  s10 f15 i1  m8  */
#define FX6_PAGE_SETTING_MAIN  36u   /* 0x02ea3e50  10 rows  s4  f0  i0  m4  */
#define FX6_PAGE_SETTING_CENTRE 80u  /* 0x02eaf208  17 rows  s2  f8  i0  m6  */
#define FX6_PAGE_AUDIO_METER    1u   /* 0x02e911f0  14 rows  s8  f0  i0  m0  */
#define FX6_PAGE_SET_BUTTON   110u   /* 0x02eb75f0  54 rows  s6  f16 i1  m30 */
#define FX6_PAGE_CLIP_GRID     18u   /* 0x02e9cef0  46 rows  s25 f1  i7  m3  */
#define FX6_PAGE_THUMB_GRID    17u   /* 0x02e9c8c0  20 rows  s14 f6  i0  m0  */

/* ----------------------------------------------------------------------
 * Representative SET-family page (0x02eb75f0, 54 rows)
 * This is the "assignable button / status assign" page: a full-screen background plus a 2-column,
 * 10-row button grid. Measured pitches:
 *     left column  x = 60,  w = 449
 *     right column x = 515, w = 449
 *     row y = 97, 169, 241, 313, 385, 457   (pitch 72, h 68)
 * ---------------------------------------------------------------------- */
static const fx6_menu_row_t fx6_set_button_page_rows[] = {
    {"No32_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No4_STATUS_ASSIGN13_BG", 0x042d5a40u, {56,49,912,477}, 0x0200c003u, 0},
    {"No9_BUTTON_01", 0x042d58d0u, {60,97,449,68}, 0x00000000u, 0},
    {"No19_BUTTON_11", 0x042d58d0u, {515,385,449,68}, 0x00000000u, 0},
    {"No18_BUTTON_10", 0x042d58d0u, {515,313,449,68}, 0x00000000u, 0},
    {"No17_BUTTON_09", 0x042d58d0u, {515,241,449,68}, 0x00000000u, 0},
    {"No16_BUTTON_08", 0x042d58d0u, {515,169,449,68}, 0x00000000u, 0},
    {"No15_BUTTON_07", 0x042d58d0u, {515,97,449,68}, 0x00000000u, 0},
    {"No14_BUTTON_06", 0x042d58d0u, {60,457,449,68}, 0x00000000u, 0},
    {"No13_BUTTON_05", 0x042d58d0u, {60,385,449,68}, 0x00000000u, 0},
    {"No12_BUTTON_04", 0x042d58d0u, {60,313,449,68}, 0x00000000u, 0},
    {"No11_BUTTON_03", 0x042d58d0u, {60,241,449,68}, 0x00000000u, 0},
    {"No10_BUTTON_02", 0x042d58d0u, {60,169,449,68}, 0x020023c4u, 0},
    {"No60_TOUCH_BUTTON_LEFT_ARROW", 0x042d58d0u, {0,50,56,475}, 0x00000000u, 0},
    {"No46_BUTTON_14", 0x042d58d0u, {515,463,449,57}, 0x00000000u, 0},
    {"No45_BUTTON_13", 0x042d58d0u, {515,402,449,57}, 0x00000000u, 0},
    {"No44_BUTTON_12", 0x042d58d0u, {515,341,449,57}, 0x00000000u, 0},
    {"No43_BUTTON_11", 0x042d58d0u, {515,280,449,57}, 0x00000000u, 0},
    {"No42_BUTTON_10", 0x042d58d0u, {515,219,449,57}, 0x00000000u, 0},
    {"No41_BUTTON_09", 0x042d58d0u, {515,158,449,57}, 0x00000000u, 0},
    {"No40_BUTTON_08", 0x042d58d0u, {515,97,449,57}, 0x00000000u, 0},
    {"No39_BUTTON_07", 0x042d58d0u, {60,463,449,57}, 0x00000000u, 0},
    {"No38_BUTTON_06", 0x042d58d0u, {60,402,449,57}, 0x00000000u, 0},
    {"No37_BUTTON_05", 0x042d58d0u, {60,341,449,57}, 0x00000000u, 0},
    {"No36_BUTTON_04", 0x042d58d0u, {60,280,449,57}, 0x00000000u, 0},
    {"No35_BUTTON_03", 0x042d58d0u, {60,219,449,57}, 0x00000000u, 0},
    {"No34_BUTTON_02", 0x042d58d0u, {60,158,449,57}, 0x00000000u, 0},
    {"No33_BUTTON_01", 0x042d58d0u, {60,97,449,57}, 0x00000000u, 0},
    {"No22_BUTTON_13", 0x042d58d0u, {743,457,221,68}, 0x00000000u, 0},
    {"No20_BUTTON_12", 0x042d58d0u, {515,457,221,68}, 0x00000000u, 0},
    {"No8_TITLE", 0x042d57f0u, {106,54,405,36}, 0x0200211eu, 0},
    {"No55_BUTTON_16", 0x042d58d0u, {743,463,221,57}, 0x00000000u, 0},
    {"No54_BUTTON_15", 0x042d58d0u, {515,463,221,57}, 0x00000000u, 0},
    {"No7_PAGE_NUMBER", 0x042d57f0u, {852,54,110,36}, 0x00000000u, 0},
    {"No59_INDEX_STRING", 0x042d57f0u, {706,54,94,36}, 0x02002e12u, 0},
    {"No57_LEFT_ARROW", 0x042d5a50u, {32,267,45,60}, 0x0200043du, 0},
    {"No53_TITLE_ICON", 0x042d57f0u, {60,51,45,42}, 0x020026c2u, 0},
    {"No52_SEPARATOR", 0x042d5a40u, {59,460,906,2}, 0x0200c00bu, 0},
    {"No51_SEPARATOR", 0x042d5a40u, {59,399,906,2}, 0x0200c00bu, 0},
    {"No50_SEPARATOR", 0x042d5a40u, {59,338,906,2}, 0x0200c00bu, 0},
    {"No49_SEPARATOR", 0x042d5a40u, {59,277,906,2}, 0x0200c00bu, 0},
    {"No48_SEPARATOR", 0x042d5a40u, {59,216,906,2}, 0x0200c00bu, 0},
    {"No47_SEPARATOR", 0x042d5a40u, {59,155,906,2}, 0x0200c00bu, 0},
    {"No28_SEPARATOR", 0x042d5a40u, {59,454,906,2}, 0x0200c00bu, 0},
    {"No27_SEPARATOR", 0x042d5a40u, {59,382,906,2}, 0x0200c00bu, 0},
    {"No26_SEPARATOR", 0x042d5a40u, {59,310,906,2}, 0x0200c00bu, 0},
    {"No25_SEPARATOR", 0x042d5a40u, {59,238,906,2}, 0x0200c00bu, 0},
    {"No24_SEPARATOR", 0x042d5a40u, {59,166,906,2}, 0x0200c00bu, 0},
    {"No23_SEPARATOR", 0x042d5a40u, {59,94,906,2}, 0x0200c00bu, 0},
    {"No58_INDEX_ARROW", 0x042d57f0u, {668,54,38,36}, 0x02002e21u, 0},
    {"No31_PAGE_SCROLL_ARROW", 0x042d57f0u, {814,54,36,36}, 0x020021d6u, 0},
    {"No29_SEPARATOR", 0x042d5a40u, {511,94,2,430}, 0x0200c00bu, 0},
    {"No30_SEPARATOR", 0x042d5a40u, {739,454,2,70}, 0x0200c00bu, 0},
    {"No56_SEPARATOR", 0x042d5a40u, {739,460,2,64}, 0x0200c00bu, 0},
};
#define FX6_SET_BUTTON_PAGE_ROWS_COUNT (sizeof(fx6_set_button_page_rows)/sizeof(fx6_set_button_page_rows[0]))

#define FX6_SET_BTN_COL_L_X  60
#define FX6_SET_BTN_COL_R_X  515
#define FX6_SET_BTN_W        449
#define FX6_SET_BTN_H        68
#define FX6_SET_BTN_Y0       97
#define FX6_SET_BTN_DY       72

/* ----------------------------------------------------------------------
 * Compact SET-family page (0x02eb6510, 7 rows) — the small confirm/list variant.
 * ---------------------------------------------------------------------- */
static const fx6_menu_row_t fx6_set_small_page_rows[] = {
    {"No7_TOUCH", 0x042d5970u, {198,138,628,342}, 0x00000000u, 0},
    {"No1_NOTIFY_5_BG", 0x042d5a50u, {198,138,628,342}, 0x0200023au, 0},
    {"No2_NOTIFY_5_TITLE", 0x042d57f0u, {220,168,584,82}, 0x020026b7u, 0},
    {"No6_NOTIFY_5_LINE4", 0x042d57f0u, {244,406,560,36}, 0x00000000u, 0},
    {"No5_NOTIFY_5_LINE3", 0x042d57f0u, {244,360,560,36}, 0x00000000u, 0},
    {"No4_NOTIFY_5_LINE2", 0x042d57f0u, {244,314,560,36}, 0x00000000u, 0},
    {"No3_NOTIFY_5_LINE1", 0x042d57f0u, {244,268,560,36}, 0x00000000u, 0},
};
#define FX6_SET_SMALL_PAGE_ROWS_COUNT \
    (sizeof(fx6_set_small_page_rows)/sizeof(fx6_set_small_page_rows[0]))

/* ----------------------------------------------------------------------
 * Setting sub-page with a 69-row grid (0x02ea0d18) — the densest page in the image.
 * ---------------------------------------------------------------------- */
static const fx6_menu_row_t fx6_setting_grid_page_rows[] = {
    {"No69_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1_Backgroundleft", 0x042d5a40u, {56,49,482,477}, 0x0200c006u, 0},
    {"No21_Backgroundright", 0x042d5a40u, {542,49,426,477}, 0x0200c006u, 0},
    {"No58_Gridlist", 0x042d59e0u, {126,102,403,415}, 0x00000000u, 0},
    {"No68_itemtouchbutton10", 0x042d58d0u, {546,493,418,44}, 0x00000000u, 0},
    {"No67_itemtouchbutton9", 0x042d58d0u, {546,449,418,44}, 0x00000000u, 0},
    {"No66_itemtouchbutton8", 0x042d58d0u, {546,405,418,44}, 0x00000000u, 0},
    {"No65_itemtouchbutton7", 0x042d58d0u, {546,361,418,44}, 0x00000000u, 0},
    {"No64_itemtouchbutton6", 0x042d58d0u, {546,317,418,44}, 0x00000000u, 0},
    {"No63_itemtouchbutton5", 0x042d58d0u, {546,273,418,44}, 0x00000000u, 0},
    {"No62_itemtouchbutton4", 0x042d58d0u, {546,229,418,44}, 0x00000000u, 0},
    {"No61_itemtouchbutton3", 0x042d58d0u, {546,185,418,44}, 0x00000000u, 0},
    {"No60_itemtouchbutton2", 0x042d58d0u, {546,141,418,44}, 0x00000000u, 0},
    {"No59_itemtouchbutton1", 0x042d58d0u, {546,97,418,44}, 0x00000000u, 0},
    {"No22_Backgroundthesecondlayeritem", 0x042d5a40u, {545,52,420,41}, 0x0200c009u, 0},
    {"No12_ItemBG", 0x042d5a40u, {126,62,401,36}, 0x0200c00du, 0},
    {"No54_Itemselectionofthesecondlayer", 0x042d57f0u, {548,54,330,36}, 0x00000000u, 0},
    {"No14_Itemselectionofthefirstlayer", 0x042d57f0u, {128,62,280,36}, 0x00000000u, 0},
    {"No41_item9inthethirdlayer", 0x042d57f0u, {551,453,254,36}, 0x00000000u, 0},
    {"No40_item8inthethirdlayer", 0x042d57f0u, {551,409,254,36}, 0x00000000u, 0},
    {"No39_item7inthethirdlayer", 0x042d57f0u, {551,365,254,36}, 0x00000000u, 0},
    {"No38_item6inthethirdlayer", 0x042d57f0u, {551,321,254,36}, 0x00000000u, 0},
    {"No37_item5inthethirdlayer", 0x042d57f0u, {551,277,254,36}, 0x00000000u, 0},
    {"No36_item4inthethirdlayer", 0x042d57f0u, {551,233,254,36}, 0x00000000u, 0},
    {"No35_item3inthethirdlayer", 0x042d57f0u, {551,189,254,36}, 0x00000000u, 0},
    {"No34_item2inthethirdlayer", 0x042d57f0u, {551,145,254,36}, 0x00000000u, 0},
    {"No33_item1inthethirdlayer", 0x042d57f0u, {551,101,254,36}, 0x00000000u, 0},
    {"No42_item10inthethirdlayer", 0x042d57f0u, {551,497,254,29}, 0x00000000u, 0},
    {"No51_value9inthethirdlayer", 0x042d57f0u, {809,453,150,36}, 0x00000000u, 0},
    {"No50_value8inthethirdlayer", 0x042d57f0u, {809,409,150,36}, 0x00000000u, 0},
    {"No49_value7inthethirdlayer", 0x042d57f0u, {809,365,150,36}, 0x00000000u, 0},
    {"No48_value6inthethirdlayer", 0x042d57f0u, {809,321,150,36}, 0x00000000u, 0},
    {"No47_value5inthethirdlayer", 0x042d57f0u, {809,277,150,36}, 0x00000000u, 0},
    {"No46_value4inthethirdlayer", 0x042d57f0u, {809,233,150,36}, 0x00000000u, 0},
    {"No45_value3inthethirdlayer", 0x042d57f0u, {809,189,150,36}, 0x00000000u, 0},
    {"No44_value2inthethirdlayer", 0x042d57f0u, {809,145,150,36}, 0x00000000u, 0},
    {"No43_value1inthethirdlayer", 0x042d57f0u, {809,101,150,36}, 0x00000000u, 0},
    {"No52_value10inthethirdlayer", 0x042d57f0u, {809,497,150,29}, 0x00000000u, 0},
    {"No53_Thirdlayershadow", 0x042d5a50u, {545,503,420,20}, 0x020001a8u, 0},
    {"No9_Menuicon8", 0x042d58d0u, {63,458,58,58}, 0x00000000u, 0},
    {"No8_Menuicon7", 0x042d58d0u, {63,401,58,58}, 0x00000000u, 0},
    {"No7_Menuicon6", 0x042d58d0u, {63,344,58,58}, 0x00000000u, 0},
    {"No6_Menuicon5", 0x042d58d0u, {63,287,58,58}, 0x00000000u, 0},
    {"No5_Menuicon4", 0x042d58d0u, {63,230,58,58}, 0x00000000u, 0},
    {"No4_Menuicon3", 0x042d58d0u, {63,173,58,58}, 0x00000000u, 0},
    {"No3_Menuicon2", 0x042d58d0u, {63,116,58,58}, 0x00000000u, 0},
    {"No2_Menuicon1", 0x042d58d0u, {63,59,58,58}, 0x00000000u, 0},
    {"No55_ItemnumberBG", 0x042d5a40u, {882,57,78,30}, 0x0200c00fu, 0},
    {"No56_itemnumber", 0x042d57f0u, {882,57,77,30}, 0x00000000u, 0},
    {"No24_Secondlayeritemshadow2", 0x042d5a50u, {545,93,420,4}, 0x02000003u, 0},
    {"No13_TabnumberBG", 0x042d5a40u, {483,66,40,28}, 0x0200c00fu, 0},
    {"No57_Tabnumber", 0x042d57f0u, {483,66,39,28}, 0x00000000u, 0},
    {"No20_Lowerleftoutsideline2", 0x042d5a40u, {57,524,481,2}, 0x0200c009u, 0},
    {"No18_Upperleftoutsideline2", 0x042d5a40u, {57,50,481,2}, 0x0200c00au, 0},
    {"No19_Lowerleftoutsideline", 0x042d5a40u, {57,523,479,2}, 0x0200c005u, 0},
    {"No32_Rightoutsideline2", 0x042d5a40u, {966,50,2,473}, 0x0200c00au, 0},
    {"No26_Leftoutsideline2", 0x042d5a40u, {543,50,2,473}, 0x0200c00au, 0},
    {"No16_Leftoutsideline2", 0x042d5a40u, {57,50,2,473}, 0x0200c00au, 0},
    {"No11_Separator2", 0x042d5a40u, {124,52,2,471}, 0x0200c00eu, 0},
    {"No10_Separator", 0x042d5a40u, {122,52,2,471}, 0x0200c001u, 0},
    {"No30_Lowerrigntoutsideline2", 0x042d5a40u, {543,524,425,2}, 0x0200c009u, 0},
    {"No29_Lowerrigntoutsideline", 0x042d5a40u, {543,523,424,2}, 0x0200c005u, 0},
    {"No28_Upperrigntoutsideline2", 0x042d5a40u, {544,50,424,2}, 0x0200c00au, 0},
    {"No17_Upperleftoutsideline", 0x042d5a40u, {57,49,479,1}, 0x0200c009u, 0},
    {"No31_Rightoutsideline", 0x042d5a40u, {965,49,1,477}, 0x0200c009u, 0},
    {"No25_Leftoutsideline", 0x042d5a40u, {542,49,1,477}, 0x0200c009u, 0},
    {"No15_Leftoutsideline", 0x042d5a40u, {56,49,1,477}, 0x0200c009u, 0},
    {"No27_Upperrigntoutsideline", 0x042d5a40u, {542,49,424,1}, 0x0200c009u, 0},
    {"No23_Secondlayeritemshadow1", 0x042d5a40u, {545,92,420,1}, 0x0200c00bu, 0},
};
#define FX6_SETTING_GRID_PAGE_ROWS_COUNT (sizeof(fx6_setting_grid_page_rows)/sizeof(fx6_setting_grid_page_rows[0]))

/* ----------------------------------------------------------------------
 * Setting sub-page, two-column layout (0x02ea20c8, 23 rows).
 * ---------------------------------------------------------------------- */
static const fx6_menu_row_t fx6_setting_two_col_page_rows[] = {
    {"No23_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1_WID_NINEPATCHIMAGE_STAGE1_BG", 0x042d5a40u, {56,49,912,477}, 0x0200c006u, 0},
    {"No21_Itemlist", 0x042d59e0u, {64,100,898,415}, 0x00000000u, 0},
    {"No11_ItemheaderBackground", 0x042d5a40u, {59,52,906,41}, 0x0200c009u, 0},
    {"No19_Iteminsecondlayer", 0x042d57f0u, {398,54,450,36}, 0x00000000u, 0},
    {"No10_ItemBackground", 0x042d5a40u, {59,52,320,37}, 0x0200c008u, 0},
    {"No16_ItemBaseshadow", 0x042d5a50u, {59,93,906,4}, 0x02000004u, 0},
    {"No13_ItemnumberBG", 0x042d5a40u, {882,57,78,30}, 0x0200c00fu, 0},
    {"No20_pagenumber", 0x042d57f0u, {884,57,74,30}, 0x00000000u, 0},
    {"No7_Loweroutsideline2", 0x042d5a40u, {58,524,910,2}, 0x0200c009u, 0},
    {"No6_Loweroutsideline", 0x042d5a40u, {57,523,908,2}, 0x0200c005u, 0},
    {"No3_Upperoutsideline2", 0x042d5a40u, {59,50,908,2}, 0x0200c00au, 0},
    {"No15_Itemheadershadow", 0x042d5a50u, {59,85,319,4}, 0x02000006u, 0},
    {"No17_Menuicon", 0x042d5a50u, {61,54,34,34}, 0x02000043u, 0},
    {"No9_Rightoutsideline2", 0x042d5a40u, {965,52,2,473}, 0x0200c00au, 0},
    {"No5_Leftoutsideline2", 0x042d5a40u, {57,50,2,473}, 0x0200c00au, 0},
    {"No2_Upperoutsideline", 0x042d5a40u, {57,49,910,1}, 0x0200c009u, 0},
    {"No14_ItemBackgroundshadow", 0x042d5a40u, {59,92,906,1}, 0x0200c00bu, 0},
    {"No12_Itemheaderseparator", 0x042d5a50u, {378,52,20,38}, 0x02000005u, 0},
    {"No18_Iteminfirstlayer", 0x042d57f0u, {97,53,280,36}, 0x00000000u, 0},
    {"No8_Rightoutsideline", 0x042d5a40u, {967,49,1,477}, 0x0200c009u, 0},
    {"No4_Leftoutsideline", 0x042d5a40u, {56,49,1,477}, 0x0200c009u, 0},
    {"No22_headertouchbutton", 0x042d58d0u, {61,53,316,36}, 0x00000000u, 0},
};
#define FX6_SETTING_TWO_COL_PAGE_ROWS_COUNT \
    (sizeof(fx6_setting_two_col_page_rows)/sizeof(fx6_setting_two_col_page_rows[0]))

/* ======================================================================
 * PHASE 16 — page 110 (SET / Assignable Button) real bindings
 * ======================================================================
 * The page carries its own title in desc+0x18, verified against the containers:
 *
 *   No8_TITLE          d18 = 0x0200211e  ->  'Assignable Button'
 *   No59_INDEX_STRING  d18 = 0x02002e12  ->  'Index'
 *   No58_INDEX_ARROW   d18 = 0x02002e21  ->  '\ue81f'   glyph
 *   No31_PAGE_SCROLL_ARROW d18 = 0x020021d6 ->  '\ue807' glyph
 *   No53_TITLE_ICON    d18 = 0x020026c2  ->  '\ue60b'   glyph (Project icon)
 *   No57_LEFT_ARROW    d18 = 0x0200043d  ->  namespace-0 image 0x43d
 *   No10_BUTTON_02     d18 = 0x020023c4  ->  'AF Speed/Sens.'
 *
 * So the *page chrome* is statically bound and needs no work. What is NOT static is the 30
 * menu_item labels: every one of those rows has desc+0x18 == 0, and — as rounds 676/677 established
 * — no descriptor in the image carries the per-cell assignment. The assignment lives in the
 * camera's assignable-button configuration, applied at run time by 0xc18548 (resid -> slot) and the
 * container cursor byte.
 *
 * Therefore the table below is a *verified label pool*, not a recovered assignment: every id
 * resolves to a real FX6 assignable-button function name, and the dynamic line can fill the 30
 * cells from it in order. Do not present it as the factory's default assignment.
 */
static const fx6_opt_t fx6_assignable_label_pool[] = {
    {0x020023c4u, "AF Speed/Sens."},
    {0x020020d0u, "White Balance"},
    {0x02004288u, "ND Filter"},
    {0x0200423du, "Peaking"},
    {0x0200423fu, "Zebra"},
    {0x0200423eu, "Marker"},
    {0x020049f5u, "Focus Magnifier"},
    {0x0200290au, "SteadyShot"},
    {0x02004246u, "S&Q Motion"},
    {0x0200425fu, "Rec Format"},
    {0x02004261u, "Codec"},
    {0x02004242u, "Timecode"},
    {0x02004253u, "Update Media"},
    {0x02004254u, "Format Media"},
    {0x0200425au, "Test Saw"},
    {0x02002e6du, "Color Bars"},
    {0x02004214u, "Flicker Reduce"},
    {0x02004217u, "Image Inversion"},
    {0x02004218u, "Lens Interface"},
    {0x02004285u, "Iris"},
    {0x02004212u, "Focus"},
    {0x02004211u, "Auto Exposure"},
    {0x02004210u, "Slow Shutter"},
    {0x02004229u, "Detail"},
    {0x0200422au, "Aperture"},
    {0x02004239u, "Monitor LUT"},
    {0x0200423au, "Output Display"},
    {0x02004241u, "Display On/Off"},
    {0x0200429fu, "WRR Setting"},
    {0x02004285u, "Iris"},
};
#define FX6_ASSIGNABLE_LABEL_POOL_COUNT \
    (sizeof(fx6_assignable_label_pool)/sizeof(fx6_assignable_label_pool[0]))

/* Page chrome constants, all verified above. */
#define FX6_SETBTN_TITLE_RESID     0x0200211eu  /* 'Assignable Button' */
#define FX6_SETBTN_INDEX_RESID     0x02002e12u  /* 'Index'             */
#define FX6_SETBTN_INDEX_ARROW     0x02002e21u  /* '\ue81f'            */
#define FX6_SETBTN_SCROLL_ARROW    0x020021d6u  /* '\ue807'            */
#define FX6_SETBTN_TITLE_ICON      0x020026c2u  /* '\ue60b'            */
#define FX6_SETBTN_LEFT_ARROW_IMG  0x0200043du  /* ns0 image           */
#define FX6_SETBTN_SEP_COLOR       0x0200c00bu  /* 444444ff            */
#define FX6_SETBTN_BG_COLOR        0x0200c003u  /* 111111df            */

/* ======================================================================
 * PHASE 16 — remaining descriptor classes
 * ======================================================================
 * A sweep of the widget *names* attached to every tag gives each class's role without guessing:
 *
 *   0x042d57d0  x58   No4_SETTING_LIST_BG_RIGHT, No1016_tcub, No2011_audio_level_meter
 *                    -> generic background/panel overlay (fill-like)
 *   0x042d57e0  x1    No3_QR_CODE                       -> QR code raster
 *   0x042d5800  x10   No9_battery_icon, No9_BATTERY      -> battery gauge
 *   0x042d5820  x3    No73_zoom_bar, No1064_zoom_bar     -> zoom bar
 *   0x042d5840  x8    No36_criate_time, No17_THUMBNAIL_PROPERTIES_MODIFIED_VALUE
 *                    -> thumbnail-properties value line
 *   0x042d5850  x7    No11_BACK, No15_BACK, No14_ITEM    -> back/item label
 *   0x042d5860  x27   No6_BLOCK_TOUCH                   -> touch blocker  (already modelled)
 *   0x042d5870  x2    No31_line_mask, No42_line_mask     -> line mask
 *   0x042d5880  x2    No11_SETTING_BAR_TOUCH, No8_SETTING_BAR -> setting bar
 *   0x042d58b0  x10   No4_PROGRESSBAR, No4_PROGRESS_BAR  -> progress bar
 *   0x042d58f0  x13   No10..No21_clip_thumbnail          -> clip thumbnail cell
 *   0x042d5910  x1    No82_level_gauge                  -> level gauge
 *   0x042d5920  x10   No2_MESSAGE_REQUEST               -> message request dialog
 *   0x042d5930  x2    No210_AUDIO_LEVEL_METER           -> audio level meter
 *   0x042d5940  x1    No21_SCAN_PROCESSING              -> scan processing
 *   0x042d5960  x5    No6_CONTEXT_MENU_PROCESSING       -> context processing
 *   0x042d5970  x60   No11_TOUCH_SCREEN                 -> full-screen touch catcher
 *   0x042d59a0  x51   No1023_gain_value, No39_focus_mode_label -> value readout with label
 *   0x042d59e0  x21   No4_LIST_MAIN, No31_Itemlist      -> list container (grid list)
 *   0x042d5a20  x4    No4_SETTING_LIST_MAIN             -> scroll-cursor list (modelled)
 *   0x042d5a40  x416  No1_BG, No23_SEPARATOR             -> fill (modelled)
 *   0x042d5a50  x382  No2_BG, No1_BG                    -> nine-patch icon/fill (modelled)
 *
 * Of these, NINE are handled by the factory at 0xc1935c, and their field maps were read straight
 * out of the branch bodies:
 *
 *   0x042d5a50  0xc1954c  desc+0x18 -> obj+0x20c ; desc+0x1c -> obj+0x230 ; desc+0x20 -> obj+0x234
 *                        ; desc+0x2c -> obj+0x23c
 *   0x042d57f0  0xc19594  desc+0x18 -> obj+0x200 ; desc+0x24 -> obj+0x208 ; desc+0x28 -> obj+0x20c
 *                        ; desc+0x1c -> obj+0x210 ; desc+0x20 -> obj+0x214 ; desc+0x2c -> obj+0xa14
 *   0x042d59a0  0xc195ec  desc+0x18 -> obj+0x230 ; desc+0x24/0x28 -> obj+0x238/+0x23c
 *                        ; desc+0x1c/0x20 -> obj+0x240/+0x244 ; obj+0x248 = 0 ; desc+0x2c -> obj+0xa44
 *   0x042d5a40  0xc19644  desc+0x18 -> obj+0x200            (colour, straight in)
 *   0x042d58d0  0xc1966c  desc+0x18 -> obj+0x21c ; desc+0x24/0x28 -> obj+0x22c/+0x234
 *                        ; desc+0x1c/0x20 -> obj+0x238/+0x23c ; obj+0x240 = 0
 *                        ; desc+0x38 (u16) -> obj+0x200 when <= 0x5b
 *   0x042d5840  0xc196cc  desc+0x24/0x28 -> obj+0x220/+0x224 ; desc+0x1c/0x20 -> obj+0x228/+0x22c
 *                        ; obj+0x230 = 0 ; desc+0x2c -> obj+0x238
 *   0x042d5960  0xc19718  desc+0x24/0x28 -> obj+0x20c/+0x210 ; desc+0x1c/0x20 -> obj+0x214/+0x218
 *                        ; obj+0x21c = 0 ; desc+0x2c -> obj+0x618
 *   0x042d57d0  0xc19754  shares the view_fill body -> desc+0x18 -> obj+0x200
 *   0x042d57e0  0xc1976c  desc+0x2c -> obj+0x370
 *
 * The other sixteen are NOT dispatched by 0xc1935c, which is why no branch exists for them: the
 * factory only knows the nine above. Their constructors are reached through the creator table at
 * 0x2911720 (40 entries), whose first constructor call per entry is:
 *
 *   [ 0] view_icon            0xc2c150   size 0x668
 *   [ 1] view_fill            0xc27660   size 0x308
 *   [ 2] view_string          0xc3af60   size 0x1388
 *   [ 4] view_menu_item       0xc3419c   size 0x19788
 *   [ 5] view_frame           0xc277c8   size 0x1178
 *   [ 6] list_scroll_cursor   0xc2d83c   size 0x239870
 *   [ 7]                     0xc2f260   size 0x1178+0x... (see creator constants)
 *   [ 8]                     0xc24bbc   [ 9] 0xc1fa44   [10] 0xc392a4   [11] 0xc3a288
 *   [12]                     0xc24338   [13] 0xc39f40   [14] 0xc2625c   [15] 0xc3cc64
 *   [16]                     0xc245bc   [17] 0xc3c4d8   [18] 0xc3994c   [19] 0xc26d48
 *   [20]                     0xc3d0e8   [21] 0xc2063c   [22] 0xc35670   [23] 0xc3e14c
 *   [24]                     0xc1f19c   [25] 0xc37ef0   [26] 0xc35e60   [27] 0xc386d8
 *   [28]                     0xc36aac   [29] 0xc36288   [30] 0xc36ca4   [31] 0xc36e90
 *   [32]                     0xc37974   [33] 0xc37838   [34] 0xc3613c   [35] 0xc3807c
 *   [36]                     0xc384b4   [37] 0xc35f94   [38] 0xc38214   [39] 0xc36bbc
 */

/* Table of the unresolved classes: tag, observed row count, class hint, factory-handled flag. */
typedef struct {
    uint32_t tag;
    uint16_t rows;
    uint8_t  factory_handled;
    const char *hint;
} fx6_class_tag_t;

static const fx6_class_tag_t fx6_class_tags[] = {
    {0x042d57d0u,  58, 1, "background/panel overlay (fill body)"},
    {0x042d57e0u,   1, 1, "QR code raster"},
    {0x042d57f0u, 693, 1, "view_string"},
    {0x042d5800u,  10, 0, "battery gauge"},
    {0x042d5820u,   3, 0, "zoom bar"},
    {0x042d5840u,   8, 1, "thumbnail-properties value line"},
    {0x042d5850u,   7, 0, "back / item label"},
    {0x042d5860u,  27, 0, "touch blocker"},
    {0x042d5870u,   2, 0, "line mask"},
    {0x042d5880u,   2, 0, "setting bar"},
    {0x042d58b0u,  10, 0, "progress bar"},
    {0x042d58d0u, 437, 1, "view_menu_item"},
    {0x042d58f0u,  13, 0, "clip thumbnail cell"},
    {0x042d5910u,   1, 0, "level gauge"},
    {0x042d5920u,  10, 0, "message request dialog"},
    {0x042d5930u,   2, 0, "audio level meter"},
    {0x042d5940u,   1, 0, "scan processing"},
    {0x042d5960u,   5, 1, "context processing"},
    {0x042d5970u,  60, 0, "full-screen touch catcher"},
    {0x042d59a0u,  51, 1, "value readout with label"},
    {0x042d59e0u,  21, 0, "list container (grid list)"},
    {0x042d5a20u,   4, 0, "scroll-cursor list"},
    {0x042d5a40u, 416, 1, "view_fill"},
    {0x042d5a50u, 382, 1, "nine-patch icon / fill"},
};
#define FX6_CLASS_TAG_COUNT (sizeof(fx6_class_tags)/sizeof(fx6_class_tags[0]))

/* The nine factory-handled tags, for a probe that wants to route through 0xc1935c. */
#define FX6_FACTORY_TAG_COUNT 9u

/* ======================================================================
 * PHASE 17 — Viewfinder HUD / status-bar pages
 * ======================================================================
 * The 128-page directory was scored by counting widget names that carry HUD vocabulary
 * (stbystate / recstate / battery / tcub / remain / media_slot / audio_level / gain / shutter /
 * white_balance / baselook / nd_ / iris / duration / codec / resolution / zoom_bar / level_gauge).
 * Fifteen pages scored >= 3; the six below are the actual HUD surfaces, and the rest are menu or
 * dialog pages that merely mention a status keyword.
 *
 *   page  1  0x02e911f0   14 rows   status strip (already exported as fx6_audio_meter_rows)
 *   page  3  0x02e917d8   71 rows   gamma-display-assist overlay, 41 icons
 *   page  8  0x02e95cc0   20 rows   tracking cancel + audio meter + gain
 *   page  9  0x02e962a8   11 rows   SHOOTING STATUS STRIP
 *   page 10  0x02e96608  253 rows   MAIN VIEWFINDER HUD
 *   page 11  0x02e9ad78   35 rows   TC value + audio meter + clip name
 *   page 58  0x02eaad68   48 rows   MEDIA STATUS (SSA / SSB / SSP)
 *
 * Page 9 is the cleanest HUD target: 11 rows that between them carry resolution, two level
 * gauges, gain, base ISO, two shutter-mode readouts, a clip name, a battery icon and two ND filter
 * readouts — i.e. the entire lower and upper status strip in one page.
 * ---------------------------------------------------------------------- */
/* HUD: shooting status strip (res/level/gain/ISO/shutter) — page base 0x02e962a8, 11 rows */
static const fx6_menu_row_t fx6_hud_shooting_strip_rows[] = {
    {"No16_resolution", 0x042d57f0u, {846,47,142,30}, 0x020050a1u, 0},
    {"No2092_level_gauge", 0x042d57d0u, {33,304,64,64}, 0x00000000u, 0},
    {"No1068_level_gauge", 0x042d57d0u, {928,327,64,64}, 0x00000000u, 0},
    {"No30_gain_value", 0x042d59a0u, {514,502,130,30}, 0x020020fcu, 0},
    {"No13_base_iso", 0x042d57f0u, {858,275,130,30}, 0x02002063u, 0},
    {"No17_shutter_mode", 0x042d59a0u, {648,502,128,30}, 0x02002009u, 0},
    {"No1014_shutter_mode", 0x042d59a0u, {618,507,128,30}, 0x02002009u, 0},
    {"No2089_clip_name_with_rec_function", 0x042d57f0u, {526,507,134,28}, 0x00000000u, 0},
    {"No2066_battery_icon", 0x042d5800u, {856,3,134,28}, 0x00000000u, 0},
    {"No58_nd_filter_mode_nd_filter_clear", 0x042d59a0u, {256,502,122,30}, 0x02002090u, 0},
    {"No1050_nd_filter_mode_nd_filter_clear", 0x042d59a0u, {144,507,122,30}, 0x02002090u, 0},
};
#define FX6_HUD_SHOOTING_STRIP_ROWS_COUNT (sizeof(fx6_hud_shooting_strip_rows)/sizeof(fx6_hud_shooting_strip_rows[0]))

/* HUD: tracking cancel + audio meter + gain — page base 0x02e95cc0, 20 rows */
static const fx6_menu_row_t fx6_hud_tracking_rows[] = {
    {"No2094_tracking_cancel_button", 0x042d57d0u, {34,3,82,82}, 0x00000000u, 0},
    {"No1113_tracking_cancel_button", 0x042d57d0u, {34,3,82,82}, 0x00000000u, 0},
    {"No2046_audio_level_meter", 0x042d57d0u, {931,391,58,112}, 0x00000000u, 0},
    {"No1067_audio_level_meter", 0x042d57d0u, {931,394,58,112}, 0x00000000u, 0},
    {"No1023_gain_value", 0x042d59a0u, {398,507,194,30}, 0x020020fcu, 0},
    {"No2067_tcub", 0x042d57d0u, {34,505,180,32}, 0x00000000u, 0},
    {"No2070_clip_name", 0x042d57f0u, {464,507,196,28}, 0x020050c4u, 0},
    {"No2091_monitor_lut", 0x042d57f0u, {754,337,169,30}, 0x0200205du, 0},
    {"No9_battery_icon", 0x042d5800u, {840,6,148,34}, 0x00000000u, 0},
    {"No1009_battery_icon", 0x042d5800u, {844,1,148,34}, 0x00000000u, 0},
    {"No76_base_look", 0x042d57f0u, {823,199,165,30}, 0x020020f5u, 0},
    {"No48_codec_name", 0x042d57f0u, {826,123,162,30}, 0x02005261u, 0},
    {"No65_frequency_scan", 0x042d57f0u, {828,85,160,30}, 0x020050acu, 0},
    {"No39_focus_mode_label", 0x042d59a0u, {36,47,160,30}, 0x02002007u, 0},
    {"No20_proxy_rec_status", 0x042d5a50u, {828,161,160,30}, 0x02000372u, 0},
    {"No19_proxy_rec_setting", 0x042d57f0u, {828,161,160,30}, 0x02005346u, 0},
    {"No1122_clip_name_clip_area_for_double_operat", 0x042d57d0u, {864,476,160,30}, 0x00000000u, 0},
    {"No1032_focus_mode_label", 0x042d59a0u, {32,3,160,30}, 0x02002007u, 0},
    {"No2044_base_look", 0x042d57f0u, {191,507,171,28}, 0x020020f5u, 0},
    {"No2050_sandq_frame_rate_fixed", 0x042d57f0u, {94,3,158,28}, 0x02002847u, 0},
};
#define FX6_HUD_TRACKING_ROWS_COUNT (sizeof(fx6_hud_tracking_rows)/sizeof(fx6_hud_tracking_rows[0]))

/* HUD: TC value + audio meter + clip name — page base 0x02e9ad78, 35 rows */
static const fx6_menu_row_t fx6_hud_tc_status_rows[] = {
    {"No423_BLOCK_TOUCH", 0x042d5860u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1_BG", 0x042d5a40u, {96,72,768,432}, 0x0200c001u, 0},
    {"No28_BG", 0x042d5a40u, {96,194,768,188}, 0x0200c008u, 0},
    {"No7_TIME_CODE_VALUE", 0x042d57f0u, {154,200,282,48}, 0xffffffffu, 0},
    {"No210_AUDIO_LEVEL_METER", 0x042d5930u, {776,206,80,164}, 0x00000000u, 0},
    {"No41_CLIP_NAME", 0x042d57f0u, {112,342,373,32}, 0x00000000u, 0},
    {"No14_CODEC_NAME", 0x042d57f0u, {493,342,180,32}, 0x02002f1eu, 0},
    {"No9_BATTERY", 0x042d5800u, {621,213,144,34}, 0x00000000u, 0},
    {"No40_CONTENT_NUMBER", 0x042d57f0u, {248,298,150,32}, 0x00000000u, 0},
    {"No122_PLAYBACK_STATUS_STRING", 0x042d57f0u, {227,256,126,32}, 0x020050d1u, 0},
    {"No422_SQ_FRAME_RATE", 0x042d57f0u, {663,298,98,32}, 0x00000000u, 0},
    {"No421_INT_REC_STATUS", 0x042d57f0u, {663,298,98,32}, 0x00000000u, 0},
    {"No34_SEPARATOR", 0x042d5a40u, {96,382,768,4}, 0x0200c00eu, 0},
    {"No33_SEPARATOR", 0x042d5a40u, {96,190,768,4}, 0x0200c00eu, 0},
    {"No15_RESOLUTION", 0x042d57f0u, {677,342,84,32}, 0x02002999u, 0},
    {"No10_ERROR_CODE", 0x042d57f0u, {99,279,52,38}, 0xffffffffu, 0},
    {"No7_TIME_DATA_TYPE", 0x042d5a50u, {104,204,44,40}, 0x00000000u, 0},
    {"No121_PLAYBACK_STATUS_ICON", 0x042d57f0u, {180,256,47,32}, 0x0200283cu, 0},
    {"No8_FRAME_RATE_UNIT", 0x042d57f0u, {514,213,42,32}, 0x0200532du, 0},
    {"No8_FRAME_RATE_VALUE_DECIMAL", 0x042d57f0u, {472,213,40,32}, 0xffffffffu, 0},
    {"No8_FRAME_RATE_VALUE_INTEGER", 0x042d57f0u, {440,213,34,32}, 0xffffffffu, 0},
    {"No202_MEDIA_PROTECT_SLOT", 0x042d5a50u, {214,297,32,34}, 0x00000000u, 0},
    {"No201_MEDIA_SLOT", 0x042d57f0u, {180,297,32,34}, 0x02002822u, 0},
    {"No10_ERROR_WARNING_ICON", 0x042d5a50u, {112,281,28,28}, 0x00000000u, 0},
    {"No32_SEPARATOR", 0x042d5a40u, {607,386,4,118}, 0x0200c00eu, 0},
    {"No31_SEPARATOR", 0x042d5a40u, {349,386,4,118}, 0x0200c00eu, 0},
    {"No30_SEPARATOR", 0x042d5a40u, {607,72,4,118}, 0x0200c00eu, 0},
    {"No29_SEPARATOR", 0x042d5a40u, {349,72,4,118}, 0x0200c00eu, 0},
    {"No105_BUTTON_05", 0x042d58d0u, {349,382,262,122}, 0x00000000u, 0},
    {"No102_BUTTON_02", 0x042d58d0u, {349,72,262,122}, 0x00000000u, 0},
    {"No106_BUTTON_06", 0x042d58d0u, {607,382,257,122}, 0x00000000u, 0},
    {"No104_BUTTON_04", 0x042d58d0u, {96,382,257,122}, 0x00000000u, 0},
    {"No103_BUTTON_03", 0x042d58d0u, {607,72,257,122}, 0x00000000u, 0},
    {"No101_BUTTON_01", 0x042d58d0u, {96,72,257,122}, 0x00000000u, 0},
    {"No2_MESSAGE_REQUEST", 0x042d5920u, {0,0,1024,540}, 0x00000000u, 0},
};
#define FX6_HUD_TC_STATUS_ROWS_COUNT (sizeof(fx6_hud_tc_status_rows)/sizeof(fx6_hud_tc_status_rows[0]))

/* HUD: media status (SSA/SSB/SSP) — page base 0x02eaad68, 48 rows */
static const fx6_menu_row_t fx6_media_status_rows[] = {
    {"No59_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No4_STATUS_MEDIA_BG", 0x042d5a40u, {56,49,912,477}, 0x0200c003u, 0},
    {"No117_SSA_INACTIVE_FRAME", 0x042d57d0u, {60,138,902,94}, 0x00000000u, 0},
    {"No116_SSB_INACTIVE_FRAME", 0x042d57d0u, {60,236,902,94}, 0x00000000u, 0},
    {"No115_SSP_INACTIVE_FRAME", 0x042d57d0u, {60,334,902,94}, 0x00000000u, 0},
    {"No119_TOUCH_BUTTON_LEFT_ARROW", 0x042d58d0u, {0,50,56,475}, 0x00000000u, 0},
    {"No87_SSB_FORMAT_BUTTON", 0x042d58d0u, {660,242,298,82}, 0x0200220fu, 0},
    {"No86_SSP_FORMAT_BUTTON", 0x042d58d0u, {660,340,298,82}, 0x0200220fu, 0},
    {"No85_SSA_FORMAT_BUTTON", 0x042d58d0u, {660,144,298,82}, 0x0200220fu, 0},
    {"No7_TITLE", 0x042d57f0u, {106,54,405,36}, 0x02002120u, 0},
    {"No8_TITLE_REMAINING", 0x042d57f0u, {224,100,240,30}, 0x02004553u, 0},
    {"No60_PAGE_BUTTON", 0x042d58d0u, {802,52,164,40}, 0x00000000u, 0},
    {"No30_SSB_REMAINING", 0x042d57f0u, {500,248,150,40}, 0x020051ceu, 0},
    {"No19_SSA_REMAINING", 0x042d57f0u, {500,150,150,40}, 0x020051ceu, 0},
    {"No108_SSP_REMAINING", 0x042d57f0u, {500,346,150,40}, 0x020051ceu, 0},
    {"No62_INDEX_BUTTON", 0x042d58d0u, {668,52,132,40}, 0x00000000u, 0},
    {"No73_SSP_LIFE", 0x042d57f0u, {500,388,150,30}, 0x00000000u, 0},
    {"No31_SSB_LIFE", 0x042d57f0u, {500,290,150,30}, 0x02002b1eu, 0},
    {"No20_SSA_LIFE", 0x042d57f0u, {500,192,150,30}, 0x02002b1eu, 0},
    {"No6_PAGE_NUMBER", 0x042d57f0u, {852,54,110,36}, 0x00000000u, 0},
    {"No23_SSB", 0x042d58b0u, {223,272,266,13}, 0x00000000u, 0},
    {"No12_SSA", 0x042d58b0u, {223,176,266,13}, 0x00000000u, 0},
    {"No109_SSP", 0x042d58b0u, {223,370,266,13}, 0x00000000u, 0},
    {"No64_INDEX_STRING", 0x042d57f0u, {706,54,94,36}, 0x02002e12u, 0},
    {"No21_SSB", 0x042d5a50u, {90,253,64,50}, 0x020003c2u, 0},
    {"No10_SSA", 0x042d5a50u, {90,157,64,50}, 0x020003c0u, 0},
    {"No100_SSP", 0x042d5a50u, {90,353,64,50}, 0x020003c4u, 0},
    {"No61_LEFT_ARROW", 0x042d5a50u, {32,267,45,60}, 0x0200043du, 0},
    {"No118_TITLE_ICON", 0x042d57f0u, {60,51,45,42}, 0x020026cfu, 0},
    {"No58_SEPARATOR", 0x042d5a40u, {59,330,906,2}, 0x0200c00bu, 0},
    {"No57_SEPARATOR", 0x042d5a40u, {59,232,906,2}, 0x0200c00bu, 0},
    {"No56_SEPARATOR", 0x042d5a40u, {59,134,906,2}, 0x0200c00bu, 0},
    {"No55_SEPARATOR", 0x042d5a40u, {59,94,906,2}, 0x0200c00bu, 0},
    {"No111_SEPARATOR", 0x042d5a40u, {60,429,906,2}, 0x0200c00bu, 0},
    {"No22_SSB_LOCK", 0x042d5a50u, {156,257,42,42}, 0x020002ffu, 0},
    {"No11_SSA_LOCK", 0x042d5a50u, {156,161,42,42}, 0x020002ffu, 0},
    {"No101_SSP_LOCK", 0x042d5a50u, {156,357,42,42}, 0x020002ffu, 0},
    {"No29_SSB_100", 0x042d57f0u, {422,284,66,22}, 0x00000000u, 0},
    {"No28_SSB_50", 0x042d57f0u, {323,284,66,22}, 0x00000000u, 0},
    {"No27_SSB_0", 0x042d57f0u, {224,284,66,22}, 0x00000000u, 0},
    {"No18_SSA_50", 0x042d57f0u, {323,188,66,22}, 0x00000000u, 0},
    {"No17_SSA_100", 0x042d57f0u, {422,188,66,22}, 0x00000000u, 0},
    {"No16_SSA_0", 0x042d57f0u, {224,188,66,22}, 0x00000000u, 0},
    {"No107_SSP_100", 0x042d57f0u, {422,382,66,22}, 0x00000000u, 0},
    {"No106_SSP_50", 0x042d57f0u, {323,382,66,22}, 0x00000000u, 0},
    {"No105_SSP_0", 0x042d57f0u, {224,382,66,22}, 0x00000000u, 0},
    {"No63_INDEX_ARROW", 0x042d57f0u, {668,54,38,36}, 0x02002e21u, 0},
    {"No5_PAGE_SCROLL_ARROW", 0x042d57f0u, {814,54,36,36}, 0x020021d6u, 0},
};
#define FX6_MEDIA_STATUS_ROWS_COUNT (sizeof(fx6_media_status_rows)/sizeof(fx6_media_status_rows[0]))

/* HUD: gamma display assist overlay — page base 0x02e917d8, 71 rows */
static const fx6_menu_row_t fx6_gamma_assist_overlay_rows[] = {
    {"No2010_gamma_display_assist", 0x042d57d0u, {813,305,110,28}, 0x00000000u, 0},
    {"No4_start_essence_mark", 0x042d57f0u, {178,89,120,24}, 0x020050e5u, 0},
    {"No2_clip_number", 0x042d57f0u, {178,51,120,24}, 0x020050e4u, 0},
    {"No2004_start_essence_mark", 0x042d57f0u, {178,89,120,24}, 0x020050e5u, 0},
    {"No2002_clip_number", 0x042d57f0u, {178,51,120,24}, 0x020050e4u, 0},
    {"No1023_sandq_frame_rate_fps", 0x042d57f0u, {928,88,64,30}, 0x020028a3u, 0},
    {"No1022_sandq_frame_rate_value", 0x042d57f0u, {928,66,64,30}, 0x00000000u, 0},
    {"No1004_gamma_display_assist", 0x042d57d0u, {864,290,58,30}, 0x00000000u, 0},
    {"No38_streamingbitrate", 0x042d57f0u, {762,8,56,30}, 0x00000000u, 0},
    {"No2031_streamingbitrate", 0x042d57f0u, {762,8,56,30}, 0x00000000u, 0},
    {"No1029_rec_look", 0x042d5a50u, {930,295,60,28}, 0x0200064au, 0},
    {"No1027_rec_format", 0x042d5a50u, {930,239,60,28}, 0x02000504u, 0},
    {"No1026_codec_name", 0x042d5a50u, {930,211,60,28}, 0x02000557u, 0},
    {"No1025_resolution", 0x042d5a50u, {930,267,60,28}, 0x02000544u, 0},
    {"No2016_play_string", 0x042d57f0u, {398,507,58,28}, 0x020050d1u, 0},
    {"No2032_rec_look", 0x042d5a50u, {34,268,60,26}, 0x0200051cu, 0},
    {"No2008_resolution", 0x042d5a50u, {34,242,60,26}, 0x0200057du, 0},
    {"No2007_rec_format", 0x042d5a50u, {34,216,60,26}, 0x020004dfu, 0},
    {"No2006_codec_name", 0x042d5a50u, {34,190,60,26}, 0x0200052au, 0},
    {"No1024_sandq_frame_rate_fixed", 0x042d57f0u, {930,93,64,24}, 0x02002847u, 0},
    {"No23_network_tethering", 0x042d5a50u, {36,6,46,32}, 0x020002a0u, 0},
    {"No2018_network_tethering", 0x042d5a50u, {36,6,46,32}, 0x020002a0u, 0},
    {"No1012_network_status", 0x042d5a50u, {306,2,46,32}, 0x020002a0u, 0},
    {"No26_upload_file_transfer_value", 0x042d57f0u, {196,8,48,30}, 0x02005463u, 0},
    {"No2021_upload_file_transfer_value", 0x042d57f0u, {196,8,48,30}, 0x02005463u, 0},
    {"No1015_upload_file_transfer_value", 0x042d57f0u, {378,4,48,30}, 0x02005463u, 0},
    {"No35_bluetooth", 0x042d5a50u, {84,6,44,32}, 0x02000418u, 0},
    {"No24_network_wifi", 0x042d5a50u, {84,6,44,32}, 0x02000247u, 0},
    {"No2028_bluetooth", 0x042d5a50u, {84,6,44,32}, 0x02000418u, 0},
    {"No2019_network_wifi", 0x042d5a50u, {84,6,44,32}, 0x02000247u, 0},
    {"No37_streamingstate", 0x042d5a50u, {716,8,46,30}, 0x02000416u, 0},
    {"No2030_streamingstate", 0x042d5a50u, {716,8,46,30}, 0x02000416u, 0},
    {"No40_digital_signature_cr_icon", 0x042d5a50u, {68,284,38,32}, 0x02000453u, 0},
    {"No36_network_wired_lan", 0x042d5a50u, {136,6,34,32}, 0x0200026au, 0},
    {"No2029_network_wired_lan", 0x042d5a50u, {136,6,34,32}, 0x0200026au, 0},
    {"No2024_media_protect_slotb", 0x042d5a50u, {880,507,32,34}, 0x0200062eu, 0},
    {"No2023_media_protect_slota", 0x042d5a50u, {731,507,32,34}, 0x0200062eu, 0},
    {"No15_play_media", 0x042d5a50u, {446,4,32,34}, 0x0200026fu, 0},
    {"No14_media_status_b", 0x042d5a50u, {36,372,32,34}, 0x02000273u, 0},
    {"No13_media_status_a", 0x042d5a50u, {36,330,32,34}, 0x0200026fu, 0},
    {"No1018_media_protect_slotb", 0x042d5a50u, {62,368,32,34}, 0x020002d3u, 0},
    {"No1017_media_protect_slota", 0x042d5a50u, {62,282,32,34}, 0x020002d3u, 0},
    {"No1008_play_media", 0x042d5a50u, {460,0,32,34}, 0x0200026fu, 0},
    {"No1007_media_status_b", 0x042d5a50u, {62,334,32,34}, 0x02000273u, 0},
    {"No1006_media_status_a", 0x042d5a50u, {62,248,32,34}, 0x0200026fu, 0},
    {"No39_digital_signature_icon", 0x042d5a50u, {36,284,32,32}, 0x02000455u, 0},
    {"No1003_frame_rate_value_integer", 0x042d57f0u, {928,115,34,30}, 0x00000000u, 0},
    {"No2015_play_status", 0x042d5a50u, {370,504,28,33}, 0x020002feu, 0},
    {"No16_play_status", 0x042d5a50u, {478,6,30,30}, 0x020002feu, 0},
    {"No1009_play_status", 0x042d5a50u, {492,2,30,30}, 0x020002feu, 0},
    {"No2013_media_status_b", 0x042d5a50u, {852,506,28,30}, 0x020004b4u, 0},
    {"No2012_media_status_a", 0x042d5a50u, {703,506,28,30}, 0x020004a9u, 0},
    {"No25_upload_file_transfer_icon", 0x042d5a50u, {170,6,26,32}, 0x020002a3u, 0},
    {"No2020_upload_file_transfer_icon", 0x042d5a50u, {170,6,26,32}, 0x020002a3u, 0},
    {"No1014_upload_file_transfer_icon", 0x042d5a50u, {352,2,26,32}, 0x020002a3u, 0},
    {"No30_media_protect_slotb", 0x042d5a50u, {70,372,28,28}, 0x020002d3u, 0},
    {"No29_media_protect_slota", 0x042d5a50u, {70,330,28,28}, 0x020002d3u, 0},
    {"No1028_frame_rate_value_decimal", 0x042d57f0u, {962,120,30,24}, 0x02004c39u, 0},
    {"No41_play_operation_panel_clip_area", 0x042d57d0u, {96,72,768,432}, 0x00000000u, 0},
    {"No1031_upper_play_operation_panel_clip_area", 0x042d57d0u, {32,0,960,70}, 0x00000000u, 0},
    {"No1030_upper_fullmenu_clip_area", 0x042d57d0u, {32,0,960,46}, 0x00000000u, 0},
    {"No1032_bottom_play_operation_panel_clip_area", 0x042d57d0u, {32,507,960,33}, 0x00000000u, 0},
    {"No1033_left_play_operation_panel_clip_area", 0x042d57d0u, {32,49,64,458}, 0x00000000u, 0},
    {"No1034_right_play_operation_panel_clip_area", 0x042d57d0u, {930,34,60,290}, 0x00000000u, 0},
    {"No2034_upper_play_operation_panel_clip_area", 0x042d57d0u, {32,0,960,36}, 0x00000000u, 0},
    {"No2035_bottom_play_operation_panel_clip_area", 0x042d57d0u, {32,504,960,36}, 0x00000000u, 0},
    {"No2036_left_play_operation_panel_clip_area", 0x042d57d0u, {32,36,64,468}, 0x00000000u, 0},
    {"No2037_right_play_operation_panel_clip_area", 0x042d57d0u, {928,36,64,345}, 0x00000000u, 0},
    {"No32_message_request", 0x042d5920u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1019_message_request", 0x042d5920u, {0,0,1024,540}, 0x00000000u, 0},
    {"No2025_message_request", 0x042d5920u, {0,0,1024,540}, 0x00000000u, 0},
};
#define FX6_GAMMA_ASSIST_OVERLAY_ROWS_COUNT (sizeof(fx6_gamma_assist_overlay_rows)/sizeof(fx6_gamma_assist_overlay_rows[0]))

/* HUD: main viewfinder status page — page base 0x02e96608, 253 rows */
static const fx6_menu_row_t fx6_hud_main_rows[] = {
    {"No4_recstate_string_slot_1st", 0x042d57f0u, {508,6,92,36}, 0x02005078u, 0},
    {"No1004_recstate_string_slot_1st", 0x042d57f0u, {522,2,92,36}, 0x02005078u, 0},
    {"No47_interval_rec_countdown", 0x042d57f0u, {578,8,110,30}, 0x0200220cu, 0},
    {"No18_shutter_value", 0x042d59a0u, {674,502,110,30}, 0x0200207cu, 0},
    {"No1040_interval_rec_countdown", 0x042d57f0u, {586,5,110,30}, 0x0200220cu, 0},
    {"No1015_shutter_value", 0x042d59a0u, {644,507,110,30}, 0x0200207cu, 0},
    {"No60_nd_filter_value_nd_transmittance", 0x042d59a0u, {278,502,106,30}, 0x02002082u, 0},
    {"No1052_nd_filter_value_nd_transmittance", 0x042d59a0u, {166,507,106,30}, 0x02002082u, 0},
    {"No2053_nd_filter_mode_nd_filter_auto_manual", 0x042d59a0u, {457,3,112,28}, 0x02002f07u, 0},
    {"No2090_gamma_display_assist", 0x042d57d0u, {813,305,110,28}, 0x00000000u, 0},
    {"No11_imager_scan_mode", 0x042d57f0u, {744,47,102,30}, 0x02002106u, 0},
    {"No73_zoom_bar", 0x042d5820u, {36,90,164,18}, 0x00000000u, 0},
    {"No2058_shutter_mode", 0x042d59a0u, {260,3,103,28}, 0x02002f07u, 0},
    {"No1121_zoom_bar_clip_area_for_double_operati", 0x042d57d0u, {864,452,160,18}, 0x00000000u, 0},
    {"No1064_zoom_bar", 0x042d5820u, {104,88,160,18}, 0x00000000u, 0},
    {"No27_rec_function", 0x042d5a50u, {364,6,78,36}, 0x0200037bu, 0},
    {"No55_white_balance_value", 0x042d59a0u, {90,460,92,30}, 0x0200208eu, 0},
    {"No1047_white_balance_value", 0x042d59a0u, {818,507,92,30}, 0x0200208eu, 0},
    {"No2015_zoom_bar", 0x042d5820u, {32,338,64,42}, 0x00000000u, 0},
    {"No15_sdi_hdmi_rec_control_recording_status", 0x042d57f0u, {109,200,87,30}, 0x020051e7u, 0},
    {"No82_level_gauge", 0x042d5910u, {796,498,68,38}, 0x00000000u, 0},
    {"No6_stbystate_slot_2nd", 0x042d57f0u, {604,6,70,36}, 0x02005079u, 0},
    {"No67_raw_output_resolution", 0x042d5a50u, {698,8,84,30}, 0x02000376u, 0},
    {"No2_stbystate_slot_1st", 0x042d57f0u, {478,6,70,36}, 0x02005079u, 0},
    {"No1020_rec_function", 0x042d5a50u, {386,1,70,36}, 0x02000565u, 0},
    {"No1006_stbystate_slot_2nd", 0x042d57f0u, {618,2,70,36}, 0x02005079u, 0},
    {"No1002_stbystate_slot_1st", 0x042d57f0u, {492,2,70,36}, 0x02005079u, 0},
    {"No2048_sandq_frame_rate", 0x042d59a0u, {94,3,88,28}, 0x020020a6u, 0},
    {"No2062_white_balance_mode", 0x042d59a0u, {698,3,87,28}, 0x02002f07u, 0},
    {"No2061_gain_value", 0x042d59a0u, {563,3,86,28}, 0x020020fcu, 0},
    {"No110_digital_extender", 0x042d57f0u, {0,85,80,30}, 0x02002cf4u, 0},
    {"No1102_usb_streaming", 0x042d5a50u, {294,2,74,32}, 0x020004dbu, 0},
    {"No21_sandq_frame_rate", 0x042d59a0u, {806,85,78,30}, 0x020020a6u, 0},
    {"No2059_shutter_value", 0x042d59a0u, {274,3,90,26}, 0x0200207cu, 0},
    {"No14_sdi_hdmi_rec_control_mode", 0x042d5a50u, {36,199,73,32}, 0x020000c6u, 0},
    {"No1011_sdi_hdmi_rec_control_mode", 0x042d5a50u, {715,2,73,32}, 0x020000c6u, 0},
    {"No8_recstate_string_slot_2nd", 0x042d57f0u, {634,6,64,36}, 0x02005078u, 0},
    {"No1008_recstate_string_slot_2nd", 0x042d57f0u, {648,2,64,36}, 0x02005078u, 0},
    {"No1019_auto_exposure_level", 0x042d59a0u, {64,507,74,30}, 0x02004720u, 0},
    {"No2055_nd_filter_value_nd_transmittance", 0x042d59a0u, {462,3,79,28}, 0x02002082u, 0},
    {"No1059_raw_output_resolution", 0x042d57f0u, {715,2,73,30}, 0x02002effu, 0},
    {"No2075_media_remain_time_unit_slotb", 0x042d57f0u, {880,507,78,28}, 0x0200528du, 0},
    {"No2074_media_remain_time_slotb", 0x042d57f0u, {880,507,78,28}, 0x020050f6u, 0},
    {"No2073_media_remain_time_unit_slota", 0x042d57f0u, {731,507,78,28}, 0x0200528du, 0},
    {"No2072_media_remain_time_slota", 0x042d57f0u, {731,507,78,28}, 0x020050f6u, 0},
    {"No123_Proxy_media_slot", 0x042d5a50u, {308,4,64,34}, 0x0200044bu, 0},
    {"No26_auto_exposure_level", 0x042d59a0u, {710,460,71,30}, 0x02004720u, 0},
    {"No2063_white_balance_value", 0x042d59a0u, {714,3,80,26}, 0x0200208eu, 0},
    {"No68_raw_rec_status", 0x042d5a50u, {782,6,56,36}, 0x02000378u, 0},
    {"No2084_recstate_string", 0x042d57f0u, {398,504,72,28}, 0x02005078u, 0},
    {"No1060_raw_rec_status", 0x042d5a50u, {788,0,56,36}, 0x02000378u, 0},
    {"No2049_frequency_scan_value", 0x042d57f0u, {182,3,70,28}, 0x00000000u, 0},
    {"No1100_media_status_proxy_stop_slotb", 0x042d5a50u, {32,366,64,30}, 0x020004a1u, 0},
    {"No1094_sandq_frame_rate_fps", 0x042d57f0u, {928,88,64,30}, 0x020028a3u, 0},
    {"No1093_sandq_frame_rate_value", 0x042d59a0u, {928,66,64,30}, 0x00000000u, 0},
    {"No2086_stbystate_with_rec_function", 0x042d57f0u, {460,504,58,33}, 0x02005079u, 0},
    {"No1109_zoom_ciz_value", 0x042d57f0u, {32,126,62,30}, 0x02002a41u, 0},
    {"No1108_zoom_ciz_icon", 0x042d57f0u, {32,99,62,30}, 0x020021bcu, 0},
    {"No1107_zoom_focal_length_unit", 0x042d57f0u, {32,67,62,30}, 0x0200287bu, 0},
    {"No1106_zoom_focal_length", 0x042d57f0u, {32,49,62,30}, 0x020021beu, 0},
    {"No1049_white_balance_hold", 0x042d57f0u, {910,507,62,30}, 0x02005281u, 0},
    {"No1031_media_remain_time_unit_slotb", 0x042d57f0u, {32,385,62,30}, 0x0200528du, 0},
    {"No1030_media_remain_time_slotb", 0x042d57f0u, {32,366,62,30}, 0x020050f6u, 0},
    {"No1028_media_remain_time_unit_slota", 0x042d57f0u, {32,299,62,30}, 0x0200528du, 0},
    {"No1027_media_remain_time_slota", 0x042d57f0u, {32,280,62,30}, 0x020050f6u, 0},
    {"No2039_steady_shot", 0x042d5a50u, {932,277,56,32}, 0x020000b1u, 0},
    {"No2026_auto_exposure_level", 0x042d59a0u, {594,44,64,28}, 0x02004720u, 0},
    {"No57_white_balance_hold", 0x042d57f0u, {184,460,58,30}, 0x02005281u, 0},
    {"No2041_steady_shot_focal_length_unit", 0x042d57f0u, {929,324,62,28}, 0x0200287bu, 0},
    {"No2040_steady_shot_focal_length", 0x042d57f0u, {929,306,62,28}, 0x00000000u, 0},
    {"No53_iris_value", 0x042d59a0u, {414,502,56,30}, 0x02002093u, 0},
    {"No2028_genlock", 0x042d5a50u, {930,35,60,28}, 0x02000503u, 0},
    {"No2027_external_tc_lock", 0x042d5a50u, {930,35,60,28}, 0x0200049fu, 0},
    {"No122_usb_stream_status_string", 0x042d57f0u, {762,8,56,30}, 0x0200294du, 0},
    {"No119_network_speed_wireless_lan_value", 0x042d57f0u, {876,461,56,30}, 0x00000000u, 0},
    {"No116_network_speed_wired_lan_value", 0x042d57f0u, {876,461,56,30}, 0x00000000u, 0},
    {"No113_network_speed_usb_tethering_value", 0x042d57f0u, {876,421,56,30}, 0x00000000u, 0},
    {"No1104_raw_output_format", 0x042d5a50u, {930,179,60,28}, 0x02000544u, 0},
    {"No1103_select_codec", 0x042d5a50u, {930,151,60,28}, 0x020005a6u, 0},
    {"No1101_imager_scan_mode_imager_size", 0x042d5a50u, {928,34,60,28}, 0x0200050fu, 0},
    {"No1099_rec_format", 0x042d5a50u, {930,239,60,28}, 0x02000504u, 0},
    {"No1091_network_speed_wireless_lan_value", 0x042d57f0u, {808,468,56,30}, 0x00000000u, 0},
    {"No1085_network_speed_wired_lan_with_usb_ethe", 0x042d57f0u, {808,428,56,30}, 0x00000000u, 0},
    {"No1082_network_speed_usb_tethering_value", 0x042d57f0u, {808,428,56,30}, 0x00000000u, 0},
    {"No105_streamingbitrate", 0x042d57f0u, {762,8,56,30}, 0x00000000u, 0},
    {"No1045_iris_value", 0x042d59a0u, {300,507,56,30}, 0x02002093u, 0},
    {"No1041_codec_name", 0x042d5a50u, {930,211,60,28}, 0x02000557u, 0},
    {"No1016_scene_file_icon", 0x042d5a50u, {930,295,60,28}, 0x02000579u, 0},
    {"No1013_resolution", 0x042d5a50u, {930,267,60,28}, 0x02000544u, 0},
    {"No1012_sdi_hdmi_rec_control_recording_status", 0x042d57f0u, {788,2,56,30}, 0x020051e7u, 0},
    {"No2038_streamingstate", 0x042d5a50u, {928,249,64,26}, 0x020004c1u, 0},
    {"No2088_recstate_string_with_rec_function", 0x042d57f0u, {460,507,58,28}, 0x02005078u, 0},
    {"No2085_rec_function", 0x042d57f0u, {370,507,58,28}, 0x02005290u, 0},
    {"No1112_gamma_display_assist", 0x042d57d0u, {864,290,58,28}, 0x00000000u, 0},
    {"No54_white_balance_mode", 0x042d59a0u, {36,460,54,30}, 0x02002008u, 0},
    {"No31_focus_position", 0x042d57f0u, {197,47,54,30}, 0x02005090u, 0},
    {"No1046_white_balance_mode", 0x042d59a0u, {764,507,54,30}, 0x02002008u, 0},
    {"No1024_focus_position", 0x042d57f0u, {193,3,54,30}, 0x02005090u, 0},
    {"No2065_white_balance_tint", 0x042d59a0u, {785,3,57,28}, 0x0200281cu, 0},
    {"No2064_white_balance_hold", 0x042d57f0u, {785,3,57,28}, 0x02005281u, 0},
    {"No2014_zoom_ciz_value", 0x042d57f0u, {76,384,57,28}, 0x00000000u, 0},
    {"No2012_zoom_focal_length_unit", 0x042d57f0u, {38,354,57,28}, 0x0200287bu, 0},
    {"No2011_zoom_focal_length", 0x042d57f0u, {38,338,57,28}, 0x00000000u, 0},
    {"No22_scene_file_icon", 0x042d59a0u, {275,460,53,30}, 0x0200208fu, 0},
    {"No28_focus_indicator", 0x042d5a50u, {168,413,44,36}, 0x020003deu, 0},
    {"No2204_focus_indicator", 0x042d5a50u, {96,467,44,36}, 0x020003deu, 0},
    {"No1021_focus_indicator", 0x042d5a50u, {52,425,44,36}, 0x020003deu, 0},
    {"No23_scene_file_no", 0x042d59a0u, {314,460,52,30}, 0x02005292u, 0},
    {"No2032_output_lut2_value", 0x042d5a50u, {930,137,60,26}, 0x02000569u, 0},
    {"No2030_output_lut1_value", 0x042d5a50u, {930,87,60,26}, 0x02000569u, 0},
    {"No2010_recording_lut", 0x042d5a50u, {34,268,60,26}, 0x02000510u, 0},
    {"No2009_rec_video_format", 0x042d5a50u, {34,242,60,26}, 0x0200057du, 0},
    {"No2008_rec_codec_format_type", 0x042d5a50u, {34,216,60,26}, 0x020004dfu, 0},
    {"No2007_rec_codec_format", 0x042d5a50u, {34,190,60,26}, 0x0200052au, 0},
    {"No2005_monitoring_desqueeze", 0x042d5a50u, {34,138,60,26}, 0x02000571u, 0},
    {"No2004_base_iso", 0x042d5a50u, {34,112,60,26}, 0x0200056eu, 0},
    {"No2003_imager_scan_mode_aspect_ratio", 0x042d5a50u, {34,86,60,26}, 0x020004abu, 0},
    {"No2002_imager_scan_mode_scan_resolution", 0x042d5a50u, {34,60,60,26}, 0x020005f9u, 0},
    {"No2001_imager_scan_mode_imager_size", 0x042d5a50u, {34,34,60,26}, 0x020004dau, 0},
    {"No1048_white_balance_tint", 0x042d59a0u, {910,507,52,30}, 0x0200281cu, 0},
    {"No24_steady_shot", 0x042d5a50u, {36,161,48,32}, 0x020000b1u, 0},
    {"No1095_sandq_frame_rate_fixed", 0x042d57f0u, {930,93,64,24}, 0x02002847u, 0},
    {"No1017_steady_shot", 0x042d5a50u, {46,165,48,32}, 0x020000b1u, 0},
    {"No2034_sdi_hdmi_rec_control_recording_status", 0x042d5a50u, {933,187,54,28}, 0x0200054au, 0},
    {"No1010_base_iso", 0x042d59a0u, {582,507,50,30}, 0x02002a2fu, 0},
    {"No70_uwp_rf_level_ch2", 0x042d5a50u, {750,83,46,32}, 0x02000389u, 0},
    {"No69_uwp_rf_level_ch1", 0x042d5a50u, {704,83,46,32}, 0x0200037fu, 0},
    {"No61_network_tethering", 0x042d5a50u, {36,6,46,32}, 0x020002a0u, 0},
    {"No131_uwp_rf_level_ch1", 0x042d5a50u, {750,83,46,32}, 0x02000393u, 0},
    {"No118_network_speed_wireless_lan_icon", 0x042d5a50u, {830,459,46,32}, 0x00000000u, 0},
    {"No115_network_speed_wired_lan_icon", 0x042d5a50u, {830,459,46,32}, 0x0200026au, 0},
    {"No112_network_speed_usb_tethering_icon", 0x042d5a50u, {830,419,46,32}, 0x020002a0u, 0},
    {"No1105_uwp_rf_level", 0x042d5a50u, {876,82,46,32}, 0x02000393u, 0},
    {"No1090_network_speed_wireless_lan_icon", 0x042d5a50u, {762,466,46,32}, 0x00000000u, 0},
    {"No1081_network_speed_usb_tethering_icon", 0x042d5a50u, {762,426,46,32}, 0x020002a0u, 0},
    {"No1062_uwp_rf_level_ch2", 0x042d5a50u, {876,122,46,32}, 0x02000389u, 0},
    {"No1061_uwp_rf_level_ch1", 0x042d5a50u, {876,82,46,32}, 0x0200037fu, 0},
    {"No1053_network_status", 0x042d5a50u, {248,2,46,32}, 0x020002a0u, 0},
    {"No37_media_remain_time_slotb", 0x042d57f0u, {68,374,49,30}, 0x020050f6u, 0},
    {"No34_media_remain_time_slota", 0x042d57f0u, {68,332,49,30}, 0x020050f6u, 0},
    {"No2082_stbystate", 0x042d57f0u, {398,504,52,28}, 0x02005079u, 0},
    {"No64_upload_file_transfer_value", 0x042d57f0u, {196,8,48,30}, 0x02005463u, 0},
    {"No1056_upload_file_transfer_value", 0x042d57f0u, {320,4,48,30}, 0x02005463u, 0},
    {"No2047_camera_id", 0x042d57f0u, {35,3,51,28}, 0x02004c70u, 0},
    {"No62_network_wifi", 0x042d5a50u, {84,6,44,32}, 0x02000247u, 0},
    {"No126_gps_icon", 0x042d5a50u, {36,122,44,32}, 0x00000000u, 0},
    {"No107_bluetooth", 0x042d5a50u, {84,6,44,32}, 0x02000418u, 0},
    {"No2016_focus_position", 0x042d57f0u, {32,471,50,28}, 0x02005090u, 0},
    {"No121_usb_stream_status_icon", 0x042d5a50u, {716,8,46,30}, 0x0200043eu, 0},
    {"No104_streamingstate", 0x042d5a50u, {716,8,46,30}, 0x02000416u, 0},
    {"No2052_iris_value", 0x042d59a0u, {385,3,53,26}, 0x02002093u, 0},
    {"No120_network_speed_wireless_lan_unit", 0x042d57f0u, {932,467,56,24}, 0x02002b74u, 0},
    {"No117_network_speed_wired_lan_unit", 0x042d57f0u, {932,467,56,24}, 0x02002b74u, 0},
    {"No114_network_speed_usb_tethering_unit", 0x042d57f0u, {932,427,56,24}, 0x02002b74u, 0},
    {"No1092_network_speed_wireless_lan_unit", 0x042d57f0u, {864,474,56,24}, 0x02002b74u, 0},
    {"No1086_network_speed_wired_lan_with_usb_ethe", 0x042d57f0u, {864,434,56,24}, 0x02002b74u, 0},
    {"No1083_network_speed_usb_tethering_unit", 0x042d57f0u, {864,434,56,24}, 0x02002b74u, 0},
    {"No40_focus_mode_tracking", 0x042d5a50u, {36,47,44,30}, 0x02000267u, 0},
    {"No2033_sdi_hdmi_rec_control_mode", 0x042d5a50u, {930,165,60,22}, 0x00000000u, 0},
    {"No2031_output_lut2_type", 0x042d5a50u, {930,115,60,22}, 0x00000000u, 0},
    {"No2029_output_lut1_type", 0x042d5a50u, {930,65,60,22}, 0x00000000u, 0},
    {"No2006_rec_format_title", 0x042d5a50u, {34,168,60,22}, 0x020004eeu, 0},
    {"No1033_focus_mode_tracking", 0x042d5a50u, {32,3,44,30}, 0x02000267u, 0},
    {"No2013_zoom_ciz_icon", 0x042d57f0u, {32,384,44,28}, 0x00000000u, 0},
    {"No2037_bluetooth", 0x042d5a50u, {939,217,42,29}, 0x02000518u, 0},
    {"No2036_network_wired_lan", 0x042d5a50u, {939,217,42,29}, 0x02000560u, 0},
    {"No2035_network_wifi", 0x042d5a50u, {939,217,42,29}, 0x02000247u, 0},
    {"No125_digital_signature_cr_icon", 0x042d5a50u, {68,284,38,32}, 0x02000453u, 0},
    {"No42_focus_mode_fase_only", 0x042d5a50u, {106,47,40,30}, 0x0200025fu, 0},
    {"No1120_focus_mode_face_only_with_face_regist", 0x042d5a50u, {102,3,40,30}, 0x020005a4u, 0},
    {"No108_focus_mode_ptz_auto_framing", 0x042d5a50u, {106,47,40,30}, 0x02000427u, 0},
    {"No1035_focus_mode_fase_only", 0x042d5a50u, {102,3,40,30}, 0x0200025fu, 0},
    {"No2019_focus_mode_tracking", 0x042d5a50u, {54,415,41,28}, 0x02000267u, 0},
    {"No5_active_media_slot_2nd", 0x042d5a50u, {572,4,32,34}, 0x02000275u, 0},
    {"No46_media_status_slotb", 0x042d5a50u, {36,372,32,34}, 0x02000273u, 0},
    {"No45_media_status_slota", 0x042d5a50u, {36,330,32,34}, 0x0200026fu, 0},
    {"No2081_media_protect_slotb", 0x042d5a50u, {852,506,32,34}, 0x020002d3u, 0},
    {"No2080_media_protect_slota", 0x042d5a50u, {703,506,32,34}, 0x020002d3u, 0},
    {"No1_active_media_slot_1st", 0x042d5a50u, {446,4,32,34}, 0x02000271u, 0},
    {"No1084_network_speed_wired_lan_with_usb_ethe", 0x042d5a50u, {762,426,34,32}, 0x0200026au, 0},
    {"No106_network_wired_lan", 0x042d5a50u, {136,6,34,32}, 0x0200026au, 0},
    {"No1039_media_status_slotb", 0x042d5a50u, {62,334,32,34}, 0x02000273u, 0},
    {"No1038_media_status_slota", 0x042d5a50u, {62,248,32,34}, 0x0200026fu, 0},
    {"No1029_media_protect_slotb", 0x042d5a50u, {62,368,32,34}, 0x020002d3u, 0},
    {"No1026_media_protect_slota", 0x042d5a50u, {62,282,32,34}, 0x020002d3u, 0},
    {"No1005_active_media_slot_2nd", 0x042d5a50u, {586,0,32,34}, 0x02000275u, 0},
    {"No1001_active_media_slot_1st", 0x042d5a50u, {460,0,32,34}, 0x02000271u, 0},
    {"No7_recstate_icon_slot_2nd", 0x042d5a50u, {604,6,30,36}, 0x02000059u, 0},
    {"No3_recstate_icon_slot_1st", 0x042d5a50u, {478,6,30,36}, 0x02000059u, 0},
    {"No1007_recstate_icon_slot_2nd", 0x042d5a50u, {618,2,30,36}, 0x02000059u, 0},
    {"No1003_recstate_icon_slot_1st", 0x042d5a50u, {492,2,30,36}, 0x02000059u, 0},
    {"No2021_focus_mode_face_only", 0x042d5a50u, {58,443,37,28}, 0x0200025fu, 0},
    {"No124_digital_signature_icon", 0x042d5a50u, {36,284,32,32}, 0x02000455u, 0},
    {"No29_gain_mode", 0x042d59a0u, {480,502,34,30}, 0x02002009u, 0},
    {"No111_focus_macro_icon", 0x042d5a50u, {273,52,34,30}, 0x02000266u, 0},
    {"No1057_frequency_scan_value_integer", 0x042d57f0u, {928,115,34,30}, 0x00000000u, 0},
    {"No1022_gain_mode", 0x042d59a0u, {364,507,34,30}, 0x02002009u, 0},
    {"No2018_focus_mode_label", 0x042d59a0u, {54,415,36,28}, 0x02002007u, 0},
    {"No1098_proxy_rec_setting_slotb", 0x042d57f0u, {31,335,33,30}, 0x020029ffu, 0},
    {"No1097_proxy_rec_setting_slota", 0x042d57f0u, {31,249,33,30}, 0x020029ffu, 0},
    {"No38_media_remain_time_unit_slotb", 0x042d57f0u, {117,379,41,24}, 0x0200528du, 0},
    {"No35_media_remain_time_unit_slota", 0x042d57f0u, {117,337,41,24}, 0x0200528du, 0},
    {"No25_auto_exposure_mode", 0x042d5a50u, {678,460,32,30}, 0x02000245u, 0},
    {"No1018_auto_exposure_mode", 0x042d5a50u, {32,507,32,30}, 0x02000245u, 0},
    {"No2087_recstate_icon_with_rec_function", 0x042d5a50u, {432,504,28,33}, 0x020004bfu, 0},
    {"No2083_recstate_icon", 0x042d5a50u, {370,504,28,33}, 0x020004bfu, 0},
    {"No44_focus_mode_fase_only_suspend", 0x042d5a50u, {166,47,30,30}, 0x02000261u, 0},
    {"No10_imager_size_mismatch", 0x042d5a50u, {714,47,30,30}, 0x02000261u, 0},
    {"No1037_focus_mode_fase_only_suspend", 0x042d5a50u, {162,3,30,30}, 0x02000261u, 0},
    {"No2060_gain_mode", 0x042d59a0u, {532,3,31,28}, 0x02002f07u, 0},
    {"No2077_media_status_slotb", 0x042d5a50u, {852,506,28,30}, 0x020004b4u, 0},
    {"No2076_media_status_slota", 0x042d5a50u, {703,506,28,30}, 0x020004a9u, 0},
    {"No2025_auto_exposure_mode", 0x042d5a50u, {564,44,30,28}, 0x0200057cu, 0},
    {"No109_gain_high_sensitivity_mode", 0x042d5a50u, {576,502,28,30}, 0x02000269u, 0},
    {"No63_upload_file_transfer_ican", 0x042d5a50u, {170,6,26,32}, 0x020002a3u, 0},
    {"No1055_upload_file_transfer_icon", 0x042d5a50u, {294,2,26,32}, 0x020002a3u, 0},
    {"No36_media_protect_slotb", 0x042d5a50u, {70,372,28,28}, 0x020002d3u, 0},
    {"No33_media_protect_slota", 0x042d5a50u, {70,330,28,28}, 0x020002d3u, 0},
    {"No2069_media_status_warning_slotb", 0x042d5a50u, {817,507,28,28}, 0x0200022eu, 0},
    {"No2068_media_status_warning_slota", 0x042d5a50u, {668,507,28,28}, 0x0200022eu, 0},
    {"No2057_error_warning", 0x042d5a50u, {548,3,28,28}, 0x0200022eu, 0},
    {"No2023_focus_mode_face_only_suspend", 0x042d5a50u, {73,415,28,28}, 0x02000261u, 0},
    {"No59_nd_filter_mode_nd_filter_auto_manual", 0x042d59a0u, {252,502,26,30}, 0x02002009u, 0},
    {"No52_iris_mode", 0x042d59a0u, {388,502,26,30}, 0x02002009u, 0},
    {"No41_focus_mode_fase_detection", 0x042d5a50u, {80,47,26,30}, 0x0200025du, 0},
    {"No1051_nd_filter_mode_nd_filter_auto_manual", 0x042d59a0u, {140,507,26,30}, 0x02002009u, 0},
    {"No1044_iris_mode", 0x042d59a0u, {274,507,26,30}, 0x02002009u, 0},
    {"No1034_focus_mode_fase_detection", 0x042d5a50u, {76,3,26,30}, 0x0200025du, 0},
    {"No2043_uwp_rf_level_ch2", 0x042d5a50u, {960,355,32,24}, 0x02000567u, 0},
    {"No2042_uwp_rf_level_ch1", 0x042d5a50u, {928,355,32,24}, 0x02000558u, 0},
    {"No2024_uwp_rf_level", 0x042d5a50u, {928,355,32,24}, 0x02000515u, 0},
    {"No1058_frequency_scan_value_decimal", 0x042d57f0u, {962,120,30,24}, 0x02004c39u, 0},
    {"No2054_nd_filter_mode_nd_filter_clear", 0x042d59a0u, {457,3,24,28}, 0x02002090u, 0},
    {"No2020_focus_mode_face_detection", 0x042d5a50u, {34,443,24,28}, 0x0200025du, 0},
    {"No56_white_balance_offset_white", 0x042d57f0u, {182,460,20,30}, 0x020020acu, 0},
    {"No43_focus_mode_fase_registrated", 0x042d5a50u, {146,47,20,30}, 0x02000264u, 0},
    {"No1110_white_balance_offset_white", 0x042d5a50u, {910,507,20,30}, 0x00000000u, 0},
    {"No1036_focus_mode_fase_registrated", 0x042d5a50u, {142,3,20,30}, 0x02000264u, 0},
    {"No2022_focus_mode_face_registrated", 0x042d5a50u, {93,443,20,28}, 0x02000264u, 0},
    {"No2017_focus_position_label", 0x042d57f0u, {82,471,20,28}, 0x0200508fu, 0},
    {"No32_focus_position_label", 0x042d57f0u, {251,52,22,24}, 0x0200508fu, 0},
    {"No1025_focus_position_label", 0x042d57f0u, {248,8,22,24}, 0x0200508fu, 0},
    {"No2056_temperature_warning", 0x042d5a50u, {530,3,18,28}, 0x020004cau, 0},
    {"No66_frequency_scan_slash", 0x042d57f0u, {886,85,16,30}, 0x02004c3bu, 0},
    {"No12_imager_scan_mode_crop", 0x042d57f0u, {794,47,16,30}, 0x0200210eu, 0},
    {"No2051_iris_mode", 0x042d59a0u, {371,3,14,26}, 0x02002f07u, 0},
    {"No1096_base_iso_latitude", 0x042d5a50u, {572,507,10,30}, 0x0200052cu, 0},
    {"No2079_media_rec_active_mark_slotb", 0x042d5a50u, {845,506,7,30}, 0x02000548u, 0},
    {"No2078_media_rec_active_mark_slota", 0x042d5a50u, {696,506,7,30}, 0x02000548u, 0},
    {"No99_message_request", 0x042d5920u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1080_message_request", 0x042d5920u, {0,0,1024,540}, 0x00000000u, 0},
    {"No2093_message_request", 0x042d5920u, {0,0,1024,540}, 0x00000000u, 0},
    {"No102_direct_menu_list", 0x042d59e0u, {0,0,0,0}, 0x00000000u, 0},
};
#define FX6_HUD_MAIN_ROWS_COUNT (sizeof(fx6_hud_main_rows)/sizeof(fx6_hud_main_rows[0]))


/* The HUD row bands, derived from the pages above. Everything is in the 0..540 frame:
 *   top strip     y = 2..47        recstate, shutter mode, ND mode, imager scan, battery, resolution
 *   upper-left    y = 47..90       zoom bar
 *   mid overlay   y = 200..338     gamma assist, video level warning, SDI/HDMI rec control
 *   lower strip   y = 460..512     white balance, ND value, shutter value, gain, clip name
 *   edge gauges   y = 304..391     level gauges at x = 33 and x = 928
 */
#define FX6_HUD_TOP_STRIP_Y    2
#define FX6_HUD_UPPER_Y       47
#define FX6_HUD_MID_Y        200
#define FX6_HUD_LOWER_Y      460
#define FX6_HUD_STRIP_H       30
#define FX6_HUD_GAUGE_L_X     33
#define FX6_HUD_GAUGE_R_X    928
#define FX6_HUD_GAUGE_Y      304
#define FX6_HUD_GAUGE_WH      64

/* Key HUD label ids, all resolved in the pages above. */
#define FX6_HUD_TXT_REC       0x02005078u   /* 'Rec'            */
#define FX6_HUD_TXT_STOP      0x020051e7u   /* 'Stop'           */
#define FX6_HUD_TXT_BATTERY   0x0200211fu   /* 'Battery'        */
#define FX6_HUD_FMT_INTERVAL  0x0200220cu   /* '\${v1:02}\\ue5d5\${v2:02}\\ue5d8' */
#define FX6_HUD_GAIN_LABEL    0x020020fcu
#define FX6_HUD_SHUTTER_LABEL 0x0200207cu
#define FX6_HUD_ND_VALUE_LABEL 0x02002082u
#define FX6_HUD_ND_MODE_LABEL 0x02002090u
#define FX6_HUD_WB_LABEL      0x0200208eu
#define FX6_HUD_BASE_ISO      0x02002063u
#define FX6_HUD_SHUTTER_MODE  0x02002009u
#define FX6_HUD_IRIS_LABEL    0x020020fcu

/* ======================================================================
 * PHASE 18 — HUD readout bindings: the formats are already in the descriptors
 * ======================================================================
 * Important finding first: the HUD readout rows on pages 9/10/11 are NOT empty. Their desc+0x18
 * holds a **format template with a PUA glyph prefix and a ${v1} placeholder**, verified against the
 * containers:
 *
 *   No30_gain_value        0x020020fc  '\ue5df${v1}'          -> gain
 *   No18_shutter_value     0x0200207c  '\ue5db${v1}'          -> shutter
 *   No60_nd_filter_value   0x02002082  '\ue5dc \ue5db${v1}'   -> ND transmittance
 *   No55_white_balance     0x0200208e  '${v1}\ue5d3'          -> white balance
 *   No47_interval_countdown 0x0200220c '${v1:02}\ue5d5${v2:02}\ue5d8'
 *   No2053_nd_mode         0x02002f07  '\ue6bd'
 *   No11_imager_scan_mode  0x02002106  'FF'
 *   No58_nd_filter_mode    0x02002090  '\ue5dc CLEAR'
 *   No13_base_iso          0x02002063  '\ue604'              (glyph only)
 *   No17_shutter_mode      0x02002009  '\ue5e4'              (glyph only)
 *   No4_recstate          0x02005078  'Rec'
 *   No15_rec_control      0x020051e7  'Stop'
 *
 * So only the *value* is missing. The table below pairs each dynamic readout with the format already
 * in its descriptor and a real, container-verified value ResID to substitute. Every value id was
 * checked to exist; a scripted audit covers all of them.
 */
#define FX6_VS_ROW_BASE      0x220u   /* row i at base + i*stride        */
#define FX6_VS_ROW_STRIDE    0x5cu
#define FX6_VS_ROW_TYPE_OFF  (-4)     /* i.e. row_base - 4 + i*stride    */
#define FX6_VS_ROW_VALUE_OFF 0x54u
#define FX6_VS_ROW_COUNT     0x610u
#define FX6_VS_DICT          0x1030u
#define FX6_VS_PARAM_NAME_TABLE 0x2911868u

/* Row types observed at row-4 in the draw loop. */
#define FX6_VS_TYPE_VALUE    1u   /* numeric value -> variant u32 (the common case) */
#define FX6_VS_TYPE_ALT2     2u
#define FX6_VS_TYPE_ALT3     3u

/* Set the u32 that `${vN}` will render. index 0 => v1, 1 => v2, ... 9 => v10.
 * Returns 0 when index is out of range or the object is null. */
static inline int fx6_view_string_set_vn(void *vs, unsigned index, uint32_t value, uint32_t type)
{
    if (!vs || index > 9u) return 0;
    char *row = (char *)vs + FX6_VS_ROW_BASE + (unsigned long)index * FX6_VS_ROW_STRIDE;
    *(int32_t *)(row + FX6_VS_ROW_TYPE_OFF) = (int32_t)type;
    *(uint32_t *)(row + FX6_VS_ROW_VALUE_OFF) = value;
    unsigned cnt = *(uint32_t *)((char *)vs + FX6_VS_ROW_COUNT);
    if (cnt <= index) *(uint32_t *)((char *)vs + FX6_VS_ROW_COUNT) = index + 1u;
    return 1;
}

/* Convenience wrappers for the HUD case, which only ever uses v1 and v2. */
static inline int fx6_view_string_set_v1(void *vs, uint32_t value)
{
    return fx6_view_string_set_vn(vs, 0, value, FX6_VS_TYPE_VALUE);
}
static inline int fx6_view_string_set_v2(void *vs, uint32_t value)
{
    return fx6_view_string_set_vn(vs, 1, value, FX6_VS_TYPE_VALUE);
}

typedef enum {
    FX6_HUD_BIND_DIRECT_RESID  = 0,  /* write primary_resid straight into +0x200 (whole string) */
    FX6_HUD_BIND_NUMERIC_V1    = 1,  /* keep the template, feed v1_int as a u32             */
    FX6_HUD_BIND_NUMERIC_V1_V2 = 2,  /* keep the template, feed v1_int and v2_int            */
} fx6_hud_bind_mode_t;

typedef struct {
    const char *widget;          /* the row's widget name, for matching at layout time */
    uint8_t  mode;               /* fx6_hud_bind_mode_t                                */
    uint32_t primary_resid;      /* DIRECT: the whole string; NUMERIC: the ${vN} template */
    uint32_t v1_int;             /* numeric value for ${v1} (NUMERIC modes only)        */
    uint32_t v2_int;             /* numeric value for ${v2} (V1_V2 mode only)           */
    const char *note;            /* what the sample reading represents                  */
} fx6_hud_slot_binding_t;

/* Every row below was re-read from its descriptor and its template verified in .uxc:
 *   '${v1}'          gain          -> 0 placeholders? no: exactly 1 (v1)
 *   '${v1}'          shutter       -> 1
 *   ' ${v1}'   ND value      -> 1
 *   '${v1}'          white balance -> 1
 *   '${v1}'          iris          -> 1
 *   '${v1}'          S&Q frame rate-> 1
 *   '${v1:02}'       WB tint       -> 1
 *   '' (no v1)       gain mode     -> 0  (glyph only, no value)
 *   '${v1:02}${v2:02}'  interval countdown -> 2 (v1 and v2)
 *   '${v1}.${v2:01}'       zoom CIZ      -> 2
 *   'Z${v1}'               zoom focal    -> 1
 *   '4096×2160'       resolution    -> 0  (fixed text, DIRECT)
 *   'Rec' / 'Stby' / 'Stop' / 'min' / '---' / 'Mbps' / 'FF' -> 0  (DIRECT)
 */
static const fx6_hud_slot_binding_t fx6_hud_default_bindings[] = {
    /* ---- page 9 ---- */
    {"No30_gain_value",      FX6_HUD_BIND_NUMERIC_V1,    0x020020fcu,  800, 0, "ISO 800"},
    {"No17_shutter_mode",    FX6_HUD_BIND_DIRECT_RESID,  0x02002009u,    0, 0, "shutter mode glyph"},
    {"No1014_shutter_mode",  FX6_HUD_BIND_DIRECT_RESID,  0x02002009u,    0, 0, "shutter mode glyph"},
    {"No58_nd_filter_mode_nd_filter_clear",  FX6_HUD_BIND_DIRECT_RESID, 0x02002090u, 0, 0, "ND CLEAR"},
    {"No1050_nd_filter_mode_nd_filter_clear",FX6_HUD_BIND_DIRECT_RESID, 0x02002090u, 0, 0, "ND CLEAR"},
    {"No16_resolution",      FX6_HUD_BIND_DIRECT_RESID,  0x020050a1u,    0, 0, "4096x2160"},
    {"No13_base_iso",        FX6_HUD_BIND_DIRECT_RESID,  0x02002063u,    0, 0, "base ISO glyph"},
    {"No2089_clip_name_with_rec_function", FX6_HUD_BIND_DIRECT_RESID, 0x020050c4u, 0, 0, "clip name"},
    {"No2066_battery_icon",  FX6_HUD_BIND_DIRECT_RESID,  0x0200211fu,    0, 0, "Battery"},
    /* ---- page 10 ---- */
    {"No18_shutter_value",   FX6_HUD_BIND_NUMERIC_V1,    0x0200207cu,  180, 0, "180 deg shutter"},
    {"No1015_shutter_value", FX6_HUD_BIND_NUMERIC_V1,    0x0200207cu,  180, 0, "180 deg shutter"},
    {"No60_nd_filter_value_nd_transmittance",  FX6_HUD_BIND_NUMERIC_V1, 0x02002082u, 3, 0, "ND 1/3"},
    {"No1052_nd_filter_value_nd_transmittance",FX6_HUD_BIND_NUMERIC_V1, 0x02002082u, 3, 0, "ND 1/3"},
    {"No55_white_balance_value", FX6_HUD_BIND_NUMERIC_V1, 0x0200208eu, 5600, 0, "5600K"},
    {"No1047_white_balance_value",FX6_HUD_BIND_NUMERIC_V1,0x0200208eu, 3200, 0, "3200K"},
    {"No2063_white_balance_value",FX6_HUD_BIND_NUMERIC_V1,0x0200208eu, 5600, 0, "5600K"},
    {"No53_iris_value",      FX6_HUD_BIND_NUMERIC_V1,    0x02002093u,    28, 0, "T2.8"},
    {"No1045_iris_value",    FX6_HUD_BIND_NUMERIC_V1,    0x02002093u,    28, 0, "T2.8"},
    {"No2052_iris_value",    FX6_HUD_BIND_NUMERIC_V1,    0x02002093u,    28, 0, "T2.8"},
    {"No2048_sandq_frame_rate", FX6_HUD_BIND_NUMERIC_V1, 0x020020a6u,    24, 0, "24P"},
    {"No21_sandq_frame_rate",   FX6_HUD_BIND_NUMERIC_V1, 0x020020a6u,    24, 0, "24P"},
    {"No2061_gain_value",    FX6_HUD_BIND_NUMERIC_V1,    0x020020fcu,   800, 0, "ISO 800"},
    {"No2059_shutter_value", FX6_HUD_BIND_NUMERIC_V1,    0x0200207cu,   180, 0, "180 deg"},
    {"No2055_nd_filter_value_nd_transmittance", FX6_HUD_BIND_NUMERIC_V1, 0x02002082u, 3, 0, "ND 1/3"},
    {"No2065_white_balance_tint",FX6_HUD_BIND_NUMERIC_V1,0x0200281cu,     0, 0, "tint 0"},
    {"No1048_white_balance_tint",FX6_HUD_BIND_NUMERIC_V1,0x0200281cu,     0, 0, "tint 0"},
    {"No47_interval_rec_countdown", FX6_HUD_BIND_NUMERIC_V1_V2, 0x0200220cu, 59, 0, "59s interval"},
    {"No1040_interval_rec_countdown",FX6_HUD_BIND_NUMERIC_V1_V2,0x0200220cu, 5, 0, "5s interval"},
    {"No1109_zoom_ciz_value",FX6_HUD_BIND_NUMERIC_V1_V2, 0x02002a41u,     2, 0, "x2.0"},
    {"No1106_zoom_focal_length",FX6_HUD_BIND_NUMERIC_V1, 0x020021beu,    35, 0, "Z35"},
    {"No2047_camera_id",     FX6_HUD_BIND_DIRECT_RESID,  0x02004c70u,    0, 0, "'A'"},
    {"No11_imager_scan_mode",FX6_HUD_BIND_DIRECT_RESID,  0x02002106u,    0, 0, "FF"},
    {"No4_recstate_string_slot_1st", FX6_HUD_BIND_DIRECT_RESID, 0x02005078u, 0, 0, "Rec"},
    {"No1004_recstate_string_slot_1st",FX6_HUD_BIND_DIRECT_RESID,0x02005078u,0, 0, "Rec"},
    {"No2_stbystate_slot_1st",FX6_HUD_BIND_DIRECT_RESID, 0x02005079u,    0, 0, "Stby"},
    {"No6_stbystate_slot_2nd",FX6_HUD_BIND_DIRECT_RESID, 0x02005079u,    0, 0, "Stby"},
    {"No15_sdi_hdmi_rec_control_recording_status", FX6_HUD_BIND_DIRECT_RESID, 0x020051e7u, 0, 0, "Stop"},
    {"No2074_media_remain_time_slotb", FX6_HUD_BIND_DIRECT_RESID, 0x020050f6u, 0, 0, "---"},
    {"No2072_media_remain_time_slota", FX6_HUD_BIND_DIRECT_RESID, 0x020050f6u, 0, 0, "---"},
    {"No2075_media_remain_time_unit_slotb",FX6_HUD_BIND_DIRECT_RESID,0x0200528du,0,0,"min"},
    {"No2073_media_remain_time_unit_slota",FX6_HUD_BIND_DIRECT_RESID,0x0200528du,0,0,"min"},
    {"No120_network_speed_wireless_lan_unit",FX6_HUD_BIND_DIRECT_RESID,0x02002b74u,0,0,"Mbps"},
    {"No117_network_speed_wired_lan_unit",  FX6_HUD_BIND_DIRECT_RESID,0x02002b74u,0,0,"Mbps"},
    {"No114_network_speed_usb_tethering_unit",FX6_HUD_BIND_DIRECT_RESID,0x02002b74u,0,0,"Mbps"},
    {"No1095_sandq_frame_rate_fixed",FX6_HUD_BIND_DIRECT_RESID,0x02002847u,0,0,"Fixed"},
    {"No1049_white_balance_hold",FX6_HUD_BIND_DIRECT_RESID, 0x02005281u, 0, 0, "Hold"},
    {"No54_white_balance_mode",FX6_HUD_BIND_DIRECT_RESID, 0x02002008u,  0, 0, "WB mode glyph"},
    {"No29_gain_mode",       FX6_HUD_BIND_DIRECT_RESID,  0x02002009u,    0, 0, "gain mode glyph"},
    {"No52_iris_mode",       FX6_HUD_BIND_DIRECT_RESID,  0x02002009u,    0, 0, "iris mode glyph"},
    /* ---- page 11 ---- */
    {"No41_CLIP_NAME",       FX6_HUD_BIND_DIRECT_RESID,  0x020050c4u,    0, 0, "clip name"},
    {"No40_CONTENT_NUMBER",  FX6_HUD_BIND_DIRECT_RESID,  0x02002385u,    0, 0, "'800'"},
    {"No14_CODEC_NAME",      FX6_HUD_BIND_DIRECT_RESID,  0x02002f1eu,    0, 0, "XAVC Intra"},
    {"No122_PLAYBACK_STATUS_STRING", FX6_HUD_BIND_DIRECT_RESID, 0x020050d1u, 0, 0, "Play"},
    {"No15_RESOLUTION",      FX6_HUD_BIND_DIRECT_RESID,  0x02002999u,    0, 0, "3840P"},
    {"No8_FRAME_RATE_UNIT",  FX6_HUD_BIND_DIRECT_RESID,  0x0200532du,    0, 0, "fps"},
    {"No422_SQ_FRAME_RATE",  FX6_HUD_BIND_DIRECT_RESID,  0x020050a7u,    0, 0, "23.98P"},
    {"No421_INT_REC_STATUS", FX6_HUD_BIND_DIRECT_RESID,  0x020050a7u,    0, 0, "23.98P"},
};
#define FX6_HUD_BINDING_COUNT \
    (sizeof(fx6_hud_default_bindings)/sizeof(fx6_hud_default_bindings[0]))

/* ONE call binds everything correctly. Never mix the modes by hand. */
static inline int fx6_apply_hud_binding(void *vs, const fx6_hud_slot_binding_t *b)
{
    if (!vs || !b) return 0;
    switch (b->mode) {
    case FX6_HUD_BIND_DIRECT_RESID:
        *(uint32_t *)((char *)vs + 0x200) = b->primary_resid;
        break;
    case FX6_HUD_BIND_NUMERIC_V1:
        if (b->primary_resid) *(uint32_t *)((char *)vs + 0x200) = b->primary_resid;
        fx6_view_string_set_v1(vs, b->v1_int);
        break;
    case FX6_HUD_BIND_NUMERIC_V1_V2:
        if (b->primary_resid) *(uint32_t *)((char *)vs + 0x200) = b->primary_resid;
        fx6_view_string_set_v1(vs, b->v1_int);
        fx6_view_string_set_v2(vs, b->v2_int);
        break;
    default:
        return 0;
    }
    *(uint8_t *)((char *)vs + 0x1fc) = 1;
    return 1;
}

/* Value families a probe can cycle through instead of the single sample above. All verified. */
static const fx6_opt_t fx6_hud_values_fps[] = {
    {0x020050a7u, "23.98P"}, {0x020050aau, "29.97P"}, {0x020050acu, "59.94P"},
};
static const fx6_opt_t fx6_hud_values_shutter[] = {
    {0x02004729u, "1/100"}, {0x0200472bu, "1/150"}, {0x0200472du, "1/200"},
    {0x0200472fu, "1/250"}, {0x0200545au, "1/2000"},
};
static const fx6_opt_t fx6_hud_values_iso[] = {
    {0x020046c8u, "ISO 640"}, {0x020046ccu, "ISO 1000"}, {0x020046d0u, "ISO 1600"},
    {0x020046d6u, "ISO 3200"}, {0x020046dcu, "ISO 6400"},
};
static const fx6_opt_t fx6_hud_values_wb[] = {
    {0x02004795u, "3200K"}, {0x02004797u, "4300K"}, {0x02004799u, "5500K"},
    {0x02004ba4u, "5600K"},
};
static const fx6_opt_t fx6_hud_values_nd[] = {
    {0x02004027u, "ND: Clear"}, {0x02004028u, "ND: 0.9"}, {0x02004029u, "ND: 1.8"},
};
static const fx6_opt_t fx6_hud_values_scan[] = {
    {0x02002104u, "FF"}, {0x02002105u, "S35"},
};
static const fx6_opt_t fx6_hud_values_aspect[] = {
    {0x02002240u, "2.39:1"}, {0x0200488bu, "16:9"},
};
static const fx6_opt_t fx6_hud_values_codec[] = {
    {0x02005261u, "XAVC-I"}, {0x02004b64u, "XAVC-I"},
};
static const fx6_opt_t fx6_hud_values_look[] = {
    {0x02002464u, "S-Cinetone"}, {0x020020f5u, "S-Cinetone"},
};
/* Network / wireless status page — page base 0x02ead870, 55 rows */
static const fx6_menu_row_t fx6_network_page_rows[] = {
    {"No48_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No4_NETWORK_BG", 0x042d5a40u, {56,49,912,477}, 0x0200c003u, 0},
    {"No55_BUTTON_SHOW_ACCESS_AUTH", 0x042d58d0u, {613,437,349,82}, 0x020027f4u, 0},
    {"No76_TOUCH_BUTTON_LEFT_ARROW", 0x042d58d0u, {0,50,56,475}, 0x00000000u, 0},
    {"No27_STATUS_USB_TETHERING", 0x042d58d0u, {294,305,240,80}, 0x020050f6u, 0},
    {"No18_STATUS_WIRED_LAN", 0x042d58d0u, {294,221,240,80}, 0x020050f6u, 0},
    {"No12_STATUS_WIRELESS_LAN", 0x042d58d0u, {294,137,240,80}, 0x020050f6u, 0},
    {"No28_BUTTON_REMOTE_USB_TETHERING", 0x042d58d0u, {539,305,194,80}, 0x020050f6u, 0},
    {"No19_BUTTON_REMOTE_WIRED_LAN", 0x042d58d0u, {539,221,194,80}, 0x020050f6u, 0},
    {"No13_BUTTON_REMOTE_WIRELESS_LAN", 0x042d58d0u, {539,137,194,80}, 0x020050f6u, 0},
    {"No1_TITLE", 0x042d57f0u, {106,54,405,36}, 0x02002122u, 0},
    {"No51_BUTTON_SETTING_BLUETOOTH", 0x042d58d0u, {185,389,104,130}, 0x020050f6u, 0},
    {"No67_BUTTON_SETTING_WIRELESS_LAN", 0x042d58d0u, {185,137,104,80}, 0x00000000u, 0},
    {"No26_BUTTON_SETTING_USB_TETHERING", 0x042d58d0u, {185,305,104,80}, 0x00000000u, 0},
    {"No54_BLUETOOTH_STATUS_2", 0x042d57f0u, {299,469,230,34}, 0x020050f6u, 0},
    {"No53_BLUETOOTH_STATUS_1", 0x042d57f0u, {299,404,230,34}, 0x020050f6u, 0},
    {"No29_IP_ADDRESS_USB_TETHERING", 0x042d57f0u, {736,328,230,34}, 0x020050f6u, 0},
    {"No20_IP_ADDRESS_WIRED_LAN", 0x042d57f0u, {736,244,230,34}, 0x020050f6u, 0},
    {"No14_IP_ADDRESS_WIRELESS_LAN", 0x042d57f0u, {736,160,230,34}, 0x020050f6u, 0},
    {"No8_LABEL_IP_ADDRESS", 0x042d57f0u, {736,101,230,30}, 0x020052c9u, 0},
    {"No6_LABEL_STATUS", 0x042d57f0u, {292,101,230,30}, 0x020052c7u, 0},
    {"No57_PAGE_BUTTON", 0x042d58d0u, {802,52,164,40}, 0x00000000u, 0},
    {"No7_LABEL_REMOTE", 0x042d57f0u, {539,101,180,30}, 0x020052c8u, 0},
    {"No73_INDEX_BUTTON", 0x042d58d0u, {668,52,132,40}, 0x00000000u, 0},
    {"No50_ITEM_BLUETOOTH", 0x042d57f0u, {64,437,121,34}, 0x02002bc6u, 0},
    {"No3_PAGE_NUMBER", 0x042d57f0u, {852,54,110,36}, 0x00000000u, 0},
    {"No9_ITEM_WIRELESS_LAN_UPPER", 0x042d57f0u, {64,149,121,30}, 0x020052bfu, 0},
    {"No71_ITEM_USB_TETHERING_MIDDLE", 0x042d57f0u, {64,330,121,30}, 0x00000000u, 0},
    {"No49_ITEM_USB_TETHERING_LOWER", 0x042d57f0u, {64,343,121,30}, 0x02002937u, 0},
    {"No25_ITEM_USB_TETHERING_UPPER", 0x042d57f0u, {64,317,121,30}, 0x0200294du, 0},
    {"No16_ITEM_WIRED_LAN_LOWER", 0x042d57f0u, {64,259,121,30}, 0x020052c3u, 0},
    {"No15_ITEM_WIRED_LAN_UPPER", 0x042d57f0u, {64,233,121,30}, 0x020052c2u, 0},
    {"No10_ITEM_WIRELESS_LAN_LOWER", 0x042d57f0u, {64,175,121,30}, 0x020052c0u, 0},
    {"No75_INDEX_STRING", 0x042d57f0u, {706,54,94,36}, 0x02002e12u, 0},
    {"No70_SETTING_USB_TETHERING", 0x042d57f0u, {190,328,90,34}, 0x020050f6u, 0},
    {"No65_SETTING_WIRELESS_LAN_MIDDLE", 0x042d57f0u, {192,160,90,34}, 0x020050f6u, 0},
    {"No17_SETTING_WIRED_LAN", 0x042d57f0u, {190,244,90,34}, 0x020050f6u, 0},
    {"No11_SETTING_WIRELESS_LAN_UPPER", 0x042d57f0u, {192,145,90,34}, 0x020050f6u, 0},
    {"No5_LABEL_SETTING", 0x042d57f0u, {185,101,100,30}, 0x020052c6u, 0},
    {"No72_LEFT_ARROW", 0x042d5a50u, {32,267,45,60}, 0x0200043du, 0},
    {"No63_SETTING_WIRELESS_LAN_LOWER", 0x042d57f0u, {192,179,90,30}, 0x020050f6u, 0},
    {"No66_TITLE_ICON", 0x042d57f0u, {60,51,45,42}, 0x020026c9u, 0},
    {"No47_SEPARATOR", 0x042d5a40u, {59,386,906,2}, 0x0200c00bu, 0},
    {"No44_SEPARATOR", 0x042d5a40u, {59,302,906,2}, 0x0200c00bu, 0},
    {"No43_SEPARATOR", 0x042d5a40u, {59,218,906,2}, 0x0200c00bu, 0},
    {"No42_SEPARATOR", 0x042d5a40u, {59,134,906,2}, 0x0200c00bu, 0},
    {"No41_SEPARATOR", 0x042d5a40u, {59,94,906,2}, 0x0200c00bu, 0},
    {"No74_INDEX_ARROW", 0x042d57f0u, {668,54,38,36}, 0x02002e21u, 0},
    {"No2_PAGE_SCROLL_ARROW", 0x042d57f0u, {814,54,36,36}, 0x020021d6u, 0},
    {"No68_BUTTON_SETTING_USB_FUNCTION", 0x042d58d0u, {185,221,104,164}, 0x00000000u, 0},
    {"No62_BUTTON_SETTING_LAN_TYPE", 0x042d58d0u, {185,137,104,164}, 0x00000000u, 0},
    {"No61_INACTIVE_FRAME_BLUETOOTH", 0x042d57d0u, {59,389,900,130}, 0x00000000u, 0},
    {"No60_INACTIVE_FRAME_USB_TETHERING", 0x042d57d0u, {59,305,900,80}, 0x00000000u, 0},
    {"No59_INACTIVE_FRAME_WIRED_LAN", 0x042d57d0u, {59,221,900,80}, 0x00000000u, 0},
    {"No58_INACTIVE_FRAME_WIRELESS_LAN", 0x042d57d0u, {59,137,900,80}, 0x00000000u, 0},
};
#define FX6_NETWORK_PAGE_ROWS_COUNT (sizeof(fx6_network_page_rows)/sizeof(fx6_network_page_rows[0]))

/* Network small confirm page — page base 0x02eb2ad8, 8 rows */
static const fx6_menu_row_t fx6_network_small_page_rows[] = {
    {"No32_BG", 0x042d5a50u, {56,49,912,477}, 0x020001d2u, 0},
    {"No31_Itemlist", 0x042d59e0u, {64,100,898,363}, 0x00000000u, 0},
    {"No17_Iteminsecondlayer", 0x042d57f0u, {516,54,405,36}, 0x00000000u, 0},
    {"No16_Iteminfirstlayer", 0x042d57f0u, {97,53,405,36}, 0x00000000u, 0},
    {"No25_NETWORK_SET_BTN_BG", 0x042d58d0u, {774,467,182,52}, 0x0200461fu, 0},
    {"No24_NETWORK_CANCEL_BTN_BG", 0x042d58d0u, {588,467,182,52}, 0x020056e8u, 0},
    {"No26_NETWORK_SEPARATOR_LINE", 0x042d5a50u, {64,463,892,2}, 0x020001fau, 0},
    {"No30_Menuicon", 0x042d5a50u, {61,54,34,34}, 0x02000043u, 0},
};
#define FX6_NETWORK_SMALL_PAGE_ROWS_COUNT (sizeof(fx6_network_small_page_rows)/sizeof(fx6_network_small_page_rows[0]))

/* Thumbnail properties page — page base 0x02e9cef0, 46 rows */
static const fx6_menu_row_t fx6_thumbnail_props_page_rows[] = {
    {"No43_yuv_cover", 0x042d5a40u, {0,0,1025,540}, 0x0200c001u, 0},
    {"No42_touch", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1_THUMBNAIL_PROPERTIES_BG", 0x042d5a50u, {0,0,1024,540}, 0x0200030du, 0},
    {"No3_THUMBNAIL_PROPERTIES_THUMBNAILUNIT_FRAME", 0x042d58f0u, {122,74,203,132}, 0x00000000u, 0},
    {"No44_touch_button_thumb", 0x042d58d0u, {126,75,195,108}, 0x00000000u, 0},
    {"No20_THUMBNAIL_PROPERTIES_CLIP_NAME_LINE3", 0x042d57f0u, {403,134,558,36}, 0x00000000u, 0},
    {"No19_THUMBNAIL_PROPERTIES_CLIP_NAME_LINE2", 0x042d57f0u, {403,98,558,36}, 0x00000000u, 0},
    {"No18_THUMBNAIL_PROPERTIES_CLIP_NAME_LINE1", 0x042d57f0u, {403,62,558,36}, 0x00000000u, 0},
    {"No2_THUMBNAIL_PROPERTIES_TITLE", 0x042d57f0u, {57,12,380,36}, 0x0200500cu, 0},
    {"No36_THUMBNAIL_PROPERTIES_RECDEVICE_VALUE", 0x042d57f0u, {587,472,374,36}, 0x00000000u, 0},
    {"No34_THUMBNAIL_PROPERTIES_RECMODE_VALUE", 0x042d57f0u, {587,426,374,36}, 0x00000000u, 0},
    {"No32_THUMBNAIL_PROPERTIES_CH_BIT_VALUE", 0x042d57f0u, {587,380,374,36}, 0x00000000u, 0},
    {"No30_THUMBNAIL_PROPERTIES_AUDIOCODEC_VALUE", 0x042d57f0u, {587,334,374,36}, 0x00000000u, 0},
    {"No28_THUMBNAIL_PROPERTIES_FPS_VALUE", 0x042d57f0u, {587,288,374,36}, 0x00000000u, 0},
    {"No26_THUMBNAIL_PROPERTIES_PICTURESIZE_VALUE", 0x042d57f0u, {587,242,374,36}, 0x00000000u, 0},
    {"No24_THUMBNAIL_PROPERTIES_VIDEOCODEC_VALUE", 0x042d57f0u, {587,196,374,36}, 0x00000000u, 0},
    {"No17_THUMBNAIL_PROPERTIES_MODIFIED_VALUE", 0x042d5840u, {64,493,318,28}, 0x00000000u, 0},
    {"No15_THUMBNAIL_PROPERTIES_CREATED_VALUE", 0x042d5840u, {64,417,318,28}, 0x00000000u, 0},
    {"No46_touch_button_next", 0x042d58d0u, {318,75,76,108}, 0x00000000u, 0},
    {"No45_touch_button_prev", 0x042d58d0u, {52,75,76,108}, 0x00000000u, 0},
    {"No9_THUMBNAIL_PROPERTIES_START_VALUE", 0x042d5840u, {205,245,176,32}, 0x00000000u, 0},
    {"No7_THUMBNAIL_PROPERTIES_TCINDEX_VALUE", 0x042d5840u, {205,199,176,32}, 0x00000000u, 0},
    {"No13_THUMBNAIL_PROPERTIES_DURATION_VALUE", 0x042d5840u, {205,337,176,32}, 0x00000000u, 0},
    {"No11_THUMBNAIL_PROPERTIES_END_VALUE", 0x042d5840u, {205,291,176,32}, 0x00000000u, 0},
    {"No35_THUMBNAIL_PROPERTIES_RECDEVICE_TITLE", 0x042d57f0u, {403,473,176,30}, 0x0200500bu, 0},
    {"No33_THUMBNAIL_PROPERTIES_RECMODE_TITLE", 0x042d57f0u, {403,427,176,30}, 0x0200500au, 0},
    {"No31_THUMBNAIL_PROPERTIES_CH_BIT_TITLE", 0x042d57f0u, {403,381,176,30}, 0x02005003u, 0},
    {"No29_THUMBNAIL_PROPERTIES_AUDIOCODEC_TITLE", 0x042d57f0u, {403,335,176,30}, 0x02005001u, 0},
    {"No27_THUMBNAIL_PROPERTIES_FPS_TITLE", 0x042d57f0u, {403,289,176,30}, 0x02005082u, 0},
    {"No25_THUMBNAIL_PROPERTIES_PICTURESIZE_TITLE", 0x042d57f0u, {403,243,176,30}, 0x02005000u, 0},
    {"No23_THUMBNAIL_PROPERTIES_VIDEOCODEC_TITLE", 0x042d57f0u, {403,197,176,30}, 0x02004fffu, 0},
    {"No38_content_num", 0x042d57f0u, {665,18,135,30}, 0x00000000u, 0},
    {"No8_THUMBNAIL_PROPERTIES_START_TITLE", 0x042d57f0u, {64,249,130,30}, 0x02004ff9u, 0},
    {"No6_THUMBNAIL_PROPERTIES_TCINDEX_TITLE", 0x042d57f0u, {64,203,130,30}, 0x02004ff8u, 0},
    {"No16_THUMBNAIL_PROPERTIES_MODIFIED_TITLE", 0x042d57f0u, {64,463,130,30}, 0x02004ffcu, 0},
    {"No14_THUMBNAIL_PROPERTIES_CREATED_TITLE", 0x042d57f0u, {64,387,130,30}, 0x02004ffbu, 0},
    {"No12_THUMBNAIL_PROPERTIES_DURATION_TITLE", 0x042d57f0u, {64,341,130,30}, 0x02005211u, 0},
    {"No10_THUMBNAIL_PROPERTIES_END_TITLE", 0x042d57f0u, {64,295,130,30}, 0x02004ffau, 0},
    {"No37_battery_icon", 0x042d5800u, {802,13,165,36}, 0x00000000u, 0},
    {"No48_digital_signature_cr_icon", 0x042d5a50u, {441,62,38,36}, 0x02000454u, 0},
    {"No47_digital_signature_icon", 0x042d5a50u, {406,62,38,36}, 0x02000452u, 0},
    {"No39_play_media", 0x042d5a50u, {592,13,32,34}, 0x0200026fu, 0},
    {"No5_THUMBNAIL_PROPERTIES_NEXT", 0x042d5a50u, {339,112,32,32}, 0x0200030fu, 0},
    {"No4_THUMBNAIL_PROPERTIES_PREV", 0x042d5a50u, {74,112,32,32}, 0x02000310u, 0},
    {"No40_play_media_protect", 0x042d5a50u, {626,13,28,28}, 0x020002d3u, 0},
    {"No41_message_request", 0x042d5920u, {0,0,1024,540}, 0x00000000u, 0},
};
#define FX6_THUMBNAIL_PROPS_PAGE_ROWS_COUNT (sizeof(fx6_thumbnail_props_page_rows)/sizeof(fx6_thumbnail_props_page_rows[0]))


/* Network page geometry: three bands of status tiles, each with a matching remote button.
 *   band y = 137 (wireless LAN), 221 (wired LAN), 305 (USB tethering)   pitch 84
 *   status tile  (294, y, 240, 80)      remote button (539, y, 194, 80)
 *   setting button (185, y, 104, 80)    left arrow (0, 50, 56, 475)
 *   title (106, 54, 405, 36) d18=0x02002122 'Network'
 *   SET (774,467,182,52) d18=0x0200461f ; CANCEL (588,467,182,52) d18=0x020056e8
 */
#define FX6_NET_BAND_Y0   137
#define FX6_NET_BAND_DY    84
#define FX6_NET_TILE_X    294
#define FX6_NET_TILE_W    240
#define FX6_NET_ROW_H      80
#define FX6_NET_REMOTE_X  539
#define FX6_NET_REMOTE_W  194
#define FX6_NET_SET_X     185
#define FX6_NET_SET_W     104
#define FX6_NET_TITLE     0x02002122u   /* 'Network' */

/* Thumbnail properties geometry: a 203x132 thumbnail at (122,74) and twelve 374-wide value
 * readouts stacked down the right side.
 *   value x = 587, w = 374, y = 196, 242, 288, 334, 380, 426, 472   (pitch 46)
 *   clip-name lines x = 403, w = 558, y = 62, 98, 134              (pitch 36)
 */
#define FX6_TP_THUMB_RECT  {122,74,203,132}
#define FX6_TP_VAL_X      587
#define FX6_TP_VAL_W      374
#define FX6_TP_VAL_Y0     196
#define FX6_TP_VAL_DY      46
#define FX6_TP_NAME_X     403
#define FX6_TP_NAME_W     558
#define FX6_TP_NAME_Y0     62
#define FX6_TP_NAME_DY     36

/* ======================================================================
 * PHASE 19 — how `${v1}` is actually resolved inside view_string
 * ======================================================================
 * The placeholder expansion happens in the text-setup helper `appFw+0xc3b4b8`, which
 * onDrawNotice calls before drawing. The relevant part is the dictionary build loop:
 *
 *   0xc3bd38  ldr  w0,[x26,#0x610]        ; row count
 *   0xc3bd3c  cmp  w0,w28 ; b.le -> done
 *   0xc3bd44  ldur w0,[x23,#-4]           ; x23 = obj+0x220 + i*0x5c ; type at -4
 *   0xc3bddc  adrp x0,#0x2911000 ; add x0,x0,#0x868   ; parameter-name table
 *   0xc3bde0  ldr  w2,[x23,#0x54]         ; VALUE at obj+0x220 + i*0x5c + 0x54
 *   0xc3bde8  ldr  x3,[x26,#0x1030]       ; the libra::Dictionary
 *   0xc3bdf0  ldr  x1,[x0,x28,lsl #3]     ; name = table[i]  ->  'v1','v2','v3',...
 *   0xc3bdfc  bl   0xb18bd0               ; libra::Variant::Variant()
 *   0xc3be10  str  w2,[x29,#0xd0]         ; variant carries the u32 value
 *   0xc3be18  bl   0xb19f40               ; Dictionary::addRow(name, variant)
 *   0xc3be20  bl   0xc3ad5c               ; append to the row array
 *   0xc3bdd0  add  x28,x28,#1             ; i++
 *   0xc3bdd4  add  x23,x23,#0x5c          ; next row
 *
 * and the name table at `appFw+0x2911868` is literally:
 *
 *   [0] 'v1'   [1] 'v2'   [2] 'v3'   [3] 'v4'   [4] 'v5'
 *   [5] 'v6'   [6] 'v7'   [7] 'v8'   [8] 'v9'   [9] 'v10'
 *
 * Conclusions:
 *
 *   1. `${vN}` is NOT substituted textually. Each row is a (type, u32 value) pair that is put into
 *      a libra::Dictionary under the key 'vN', and the TextSprite renders the template with that
 *      dictionary. So the value is a **32-bit integer**, not a string pointer and not a ResID.
 *   2. The values live in an inline array inside the view_string object:
 *          row i at  obj + 0x220 + i*0x5c
 *          type     at  row - 4        (1 = value, 2 and 3 = other renderings)
 *          value    at  row + 0x54
 *   3. The row count is at  obj + 0x610. When it is 0 (a ctor-only widget) no dictionary is built and
 *      any `${vN}` in the template renders as nothing — which is the same failure mode as Phase 7.
 *   4. Formatting hints such as `${v2:02}` are handled by the same path; only the integer value and
 *      the row type matter.
 */

/* Paint/direct-menu page (largest fill page) -- page base 0x02ea7648, 176 rows */
static const fx6_menu_row_t fx6_paint_direct_page_rows[] = {
    {"No48_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No4_PANEL_BG", 0x042d5a40u, {56,49,912,477}, 0x0200c003u, 0},
    {"No57_TOUCH_BUTTON_LEFT_ARROW", 0x042d58d0u, {0,50,56,475}, 0x00000000u, 0},
    {"No20_TOUCHBUTTON_CH4_LEVELMETER", 0x042d58d0u, {144,372,310,76}, 0x00000000u, 0},
    {"No19_TOUCHBUTTON_CH3_LEVELMETER", 0x042d58d0u, {144,292,310,76}, 0x00000000u, 0},
    {"No14_CH4_LEVEL_BASE", 0x042d5a50u, {148,376,300,68}, 0x020003c7u, 0},
    {"No13_CH3_LEVEL_BASE", 0x042d5a50u, {148,296,300,68}, 0x020003c7u, 0},
    {"No12_CH2_LEVEL_BASE", 0x042d5a50u, {148,216,300,68}, 0x020003c7u, 0},
    {"No11_CH1_LEVEL_BASE", 0x042d5a50u, {148,136,300,68}, 0x020003c7u, 0},
    {"No36_TOUCHBUTTON_SETTING_4", 0x042d58d0u, {740,452,222,70}, 0x00000000u, 0},
    {"No34_TOUCHBUTTON_SETTING_2", 0x042d58d0u, {286,452,222,70}, 0x00000000u, 0},
    {"No35_TOUCHBUTTON_SETTING_3", 0x042d58d0u, {514,452,220,70}, 0x00000000u, 0},
    {"No33_TOUCHBUTTON_SETTING_1", 0x042d58d0u, {60,452,220,70}, 0x00000000u, 0},
    {"No37_TITLE", 0x042d57f0u, {106,54,405,36}, 0x0200211bu, 0},
    {"No24_TOUCHBUTTON_CH4_SOURCE", 0x042d58d0u, {460,372,184,76}, 0x00000000u, 0},
    {"No23_TOUCHBUTTON_CH3_SOURCE", 0x042d58d0u, {460,292,184,76}, 0x00000000u, 0},
    {"No22_TOUCHBUTTON_CH2_SOURCE", 0x042d58d0u, {460,212,184,76}, 0x00000000u, 0},
    {"No21_TOUCHBUTTON_CH1_SOURCE", 0x042d58d0u, {460,132,184,76}, 0x00000000u, 0},
    {"No32_TOUCHBUTTON_CH4_WINDFILTER", 0x042d58d0u, {800,372,162,76}, 0x00000000u, 0},
    {"No31_TOUCHBUTTON_CH3_WINDFILTER", 0x042d58d0u, {800,292,162,76}, 0x00000000u, 0},
    {"No30_TOUCHBUTTON_CH2_WINDFILTER", 0x042d58d0u, {800,212,162,76}, 0x00000000u, 0},
    {"No29_TOUCHBUTTON_CH1_WINDFILTER", 0x042d58d0u, {800,132,162,76}, 0x00000000u, 0},
    {"No28_TOUCHBUTTON_CH4_REF", 0x042d58d0u, {650,372,144,76}, 0x00000000u, 0},
    {"No27_TOUCHBUTTON_CH3_REF", 0x042d58d0u, {650,292,144,76}, 0x00000000u, 0},
    {"No26_TOUCHBUTTON_CH2_REF", 0x042d58d0u, {650,212,144,76}, 0x00000000u, 0},
    {"No25_TOUCHBUTTON_CH1_REF", 0x042d58d0u, {650,132,144,76}, 0x00000000u, 0},
    {"No7_LABEL_LEVEL", 0x042d57f0u, {144,97,284,30}, 0x020043c9u, 0},
    {"No47_PAGE_BUTTON", 0x042d58d0u, {802,52,164,40}, 0x00000000u, 0},
    {"No18_TOUCHBUTTON_CH4_LEVELCONTROL", 0x042d58d0u, {60,372,78,76}, 0x00000000u, 0},
    {"No17_TOUCHBUTTON_CH3_LEVELCONTROL", 0x042d58d0u, {60,292,78,76}, 0x00000000u, 0},
    {"No16_TOUCHBUTTON_CH2_LEVELCONTROL", 0x042d58d0u, {60,212,78,76}, 0x00000000u, 0},
    {"No15_TOUCHBUTTON_CH1_LEVELCONTROL", 0x042d58d0u, {60,132,78,76}, 0x00000000u, 0},
    {"No54_INDEX_BUTTON", 0x042d58d0u, {668,52,132,40}, 0x00000000u, 0},
    {"No8_LABEL_SOURCE", 0x042d57f0u, {460,97,170,30}, 0x02005117u, 0},
    {"No6_LABEL_TITLE_RIGHT", 0x042d57f0u, {822,54,140,36}, 0x00000000u, 0},
    {"No10_LABEL_WINDFILTER", 0x042d57f0u, {804,97,150,30}, 0x02005119u, 0},
    {"No47_PAGE_NUMBER", 0x042d57f0u, {852,54,110,36}, 0x00000000u, 0},
    {"No9_LABEL_REF", 0x042d57f0u, {650,97,130,30}, 0x02005125u, 0},
    {"No56_INDEX_STRING", 0x042d57f0u, {706,54,94,36}, 0x02002e12u, 0},
    {"No52_TITLE_ICON", 0x042d57f0u, {60,51,45,42}, 0x020026c6u, 0},
    {"No43_SEPARATOR", 0x042d5a40u, {59,449,906,2}, 0x0200c00bu, 0},
    {"No42_SEPARATOR", 0x042d5a40u, {59,369,906,2}, 0x0200c00bu, 0},
    {"No41_SEPARATOR", 0x042d5a40u, {59,289,906,2}, 0x0200c00bu, 0},
    {"No40_SEPARATOR", 0x042d5a40u, {59,209,906,2}, 0x0200c00bu, 0},
    {"No39_SEPARATOR", 0x042d5a40u, {59,127,906,2}, 0x0200c00bu, 0},
    {"No38_SEPARATOR", 0x042d5a40u, {59,94,906,2}, 0x0200c00bu, 0},
    {"No55_INDEX_ARROW", 0x042d57f0u, {668,54,38,36}, 0x02002e21u, 0},
    {"No47_PAGE_ARROW", 0x042d57f0u, {814,54,36,36}, 0x020021d6u, 0},
    {"No52_SEPARATOR", 0x042d5a40u, {796,127,2,322}, 0x0200c00bu, 0},
    {"No51_SEPARATOR", 0x042d5a40u, {646,127,2,322}, 0x0200c00bu, 0},
    {"No50_SEPARATOR", 0x042d5a40u, {456,127,2,322}, 0x0200c00bu, 0},
    {"No49_SEPARATOR", 0x042d5a40u, {140,289,2,160}, 0x0200c00bu, 0},
    {"No14_CH4_LEVEL_9", 0x042d5a40u, {254,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_8", 0x042d5a40u, {242,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_7", 0x042d5a40u, {230,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_6", 0x042d5a40u, {218,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_5", 0x042d5a40u, {206,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_4", 0x042d5a40u, {194,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_3", 0x042d5a40u, {182,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_24", 0x042d5a40u, {434,384,8,34}, 0x0200c011u, 0},
    {"No14_CH4_LEVEL_23", 0x042d5a40u, {422,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_22", 0x042d5a40u, {410,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_21", 0x042d5a40u, {398,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_20", 0x042d5a40u, {386,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_2", 0x042d5a40u, {170,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_19", 0x042d5a40u, {374,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_18", 0x042d5a40u, {362,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_17", 0x042d5a40u, {350,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_16", 0x042d5a40u, {338,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_15", 0x042d5a40u, {326,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_14", 0x042d5a40u, {314,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_13", 0x042d5a40u, {302,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_12", 0x042d5a40u, {290,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_11", 0x042d5a40u, {278,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_10", 0x042d5a40u, {266,384,8,34}, 0x0200c010u, 0},
    {"No14_CH4_LEVEL_1", 0x042d5a40u, {158,384,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_9", 0x042d5a40u, {254,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_8", 0x042d5a40u, {242,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_7", 0x042d5a40u, {230,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_6", 0x042d5a40u, {218,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_5", 0x042d5a40u, {206,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_4", 0x042d5a40u, {194,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_3", 0x042d5a40u, {182,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_24", 0x042d5a40u, {434,304,8,34}, 0x0200c011u, 0},
    {"No13_CH3_LEVEL_23", 0x042d5a40u, {422,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_22", 0x042d5a40u, {410,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_21", 0x042d5a40u, {398,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_20", 0x042d5a40u, {386,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_2", 0x042d5a40u, {170,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_19", 0x042d5a40u, {374,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_18", 0x042d5a40u, {362,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_17", 0x042d5a40u, {350,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_16", 0x042d5a40u, {338,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_15", 0x042d5a40u, {326,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_14", 0x042d5a40u, {314,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_13", 0x042d5a40u, {302,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_12", 0x042d5a40u, {290,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_11", 0x042d5a40u, {278,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_10", 0x042d5a40u, {266,304,8,34}, 0x0200c010u, 0},
    {"No13_CH3_LEVEL_1", 0x042d5a40u, {158,304,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_9", 0x042d5a40u, {254,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_8", 0x042d5a40u, {242,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_7", 0x042d5a40u, {230,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_6", 0x042d5a40u, {218,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_5", 0x042d5a40u, {206,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_4", 0x042d5a40u, {194,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_3", 0x042d5a40u, {182,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_24", 0x042d5a40u, {434,224,8,34}, 0x0200c011u, 0},
    {"No12_CH2_LEVEL_23", 0x042d5a40u, {422,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_22", 0x042d5a40u, {410,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_21", 0x042d5a40u, {398,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_20", 0x042d5a40u, {386,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_2", 0x042d5a40u, {170,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_19", 0x042d5a40u, {374,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_18", 0x042d5a40u, {362,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_17", 0x042d5a40u, {350,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_16", 0x042d5a40u, {338,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_15", 0x042d5a40u, {326,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_14", 0x042d5a40u, {314,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_13", 0x042d5a40u, {302,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_12", 0x042d5a40u, {290,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_11", 0x042d5a40u, {278,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_10", 0x042d5a40u, {266,224,8,34}, 0x0200c010u, 0},
    {"No12_CH2_LEVEL_1", 0x042d5a40u, {158,224,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_9", 0x042d5a40u, {254,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_8", 0x042d5a40u, {242,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_7", 0x042d5a40u, {230,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_6", 0x042d5a40u, {218,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_5", 0x042d5a40u, {206,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_4", 0x042d5a40u, {194,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_3", 0x042d5a40u, {182,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_24", 0x042d5a40u, {434,144,8,34}, 0x0200c011u, 0},
    {"No11_CH1_LEVEL_23", 0x042d5a40u, {422,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_22", 0x042d5a40u, {410,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_21", 0x042d5a40u, {398,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_20", 0x042d5a40u, {386,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_2", 0x042d5a40u, {170,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_19", 0x042d5a40u, {374,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_18", 0x042d5a40u, {362,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_17", 0x042d5a40u, {350,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_16", 0x042d5a40u, {338,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_15", 0x042d5a40u, {326,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_14", 0x042d5a40u, {314,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_13", 0x042d5a40u, {302,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_12", 0x042d5a40u, {290,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_11", 0x042d5a40u, {278,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_10", 0x042d5a40u, {266,144,8,34}, 0x0200c010u, 0},
    {"No11_CH1_LEVEL_1", 0x042d5a40u, {158,144,8,34}, 0x0200c010u, 0},
    {"No46_SEPARATOR", 0x042d5a40u, {736,449,2,74}, 0x0200c00bu, 0},
    {"No45_SEPARATOR", 0x042d5a40u, {510,449,2,74}, 0x0200c00bu, 0},
    {"No44_SEPARATOR", 0x042d5a40u, {282,449,2,74}, 0x0200c00bu, 0},
    {"No14_CH4_REF_LEVEL_EBUL", 0x042d5a50u, {364,377,6,6}, 0x0200030cu, 0},
    {"No14_CH4_REF_LEVEL_20DB", 0x042d5a50u, {304,377,6,6}, 0x0200030bu, 0},
    {"No14_CH4_REF_LEVEL_18DB", 0x042d5a50u, {316,377,6,6}, 0x0200030bu, 0},
    {"No14_CH4_REF_LEVEL_16DB", 0x042d5a50u, {328,377,6,6}, 0x0200030bu, 0},
    {"No14_CH4_REF_LEVEL_12DB", 0x042d5a50u, {352,377,6,6}, 0x0200030bu, 0},
    {"No13_CH3_REF_LEVEL_EBUL", 0x042d5a50u, {364,297,6,6}, 0x0200030cu, 0},
    {"No13_CH3_REF_LEVEL_20DB", 0x042d5a50u, {304,297,6,6}, 0x0200030bu, 0},
    {"No13_CH3_REF_LEVEL_18DB", 0x042d5a50u, {316,297,6,6}, 0x0200030bu, 0},
    {"No13_CH3_REF_LEVEL_16DB", 0x042d5a50u, {328,297,6,6}, 0x0200030bu, 0},
    {"No13_CH3_REF_LEVEL_12DB", 0x042d5a50u, {352,297,6,6}, 0x0200030bu, 0},
    {"No12_CH2_REF_LEVEL_EBUL", 0x042d5a50u, {364,217,6,6}, 0x0200030cu, 0},
    {"No12_CH2_REF_LEVEL_20DB", 0x042d5a50u, {304,217,6,6}, 0x0200030bu, 0},
    {"No12_CH2_REF_LEVEL_18DB", 0x042d5a50u, {316,217,6,6}, 0x0200030bu, 0},
    {"No12_CH2_REF_LEVEL_16DB", 0x042d5a50u, {328,217,6,6}, 0x0200030bu, 0},
    {"No12_CH2_REF_LEVEL_12DB", 0x042d5a50u, {352,217,6,6}, 0x0200030bu, 0},
    {"No11_CH1_REF_LEVEL_EBUL", 0x042d5a50u, {364,137,6,6}, 0x0200030cu, 0},
    {"No11_CH1_REF_LEVEL_20DB", 0x042d5a50u, {304,137,6,6}, 0x0200030bu, 0},
    {"No11_CH1_REF_LEVEL_18DB", 0x042d5a50u, {316,137,6,6}, 0x0200030bu, 0},
    {"No11_CH1_REF_LEVEL_16DB", 0x042d5a50u, {328,137,6,6}, 0x0200030bu, 0},
    {"No11_CH1_REF_LEVEL_12DB", 0x042d5a50u, {352,137,6,6}, 0x0200030bu, 0},
    {"No14_HIGHLIGHT_CH4", 0x042d57d0u, {60,372,902,76}, 0x00000000u, 0},
    {"No13_HIGHLIGHT_CH3", 0x042d57d0u, {60,292,902,76}, 0x00000000u, 0},
    {"No12_HIGHLIGHT_CH2", 0x042d57d0u, {60,212,902,76}, 0x00000000u, 0},
    {"No11_HIGHLIGHT_CH1", 0x042d57d0u, {60,132,902,76}, 0x00000000u, 0},
    {"No53_LEFT_ARROW", 0x042d5a50u, {32,267,45,60}, 0x0200043du, 0},
};
#define FX6_PAINT_DIRECT_PAGE_ROWS_COUNT (sizeof(fx6_paint_direct_page_rows)/sizeof(fx6_paint_direct_page_rows[0]))

/* Paint overlay page (37 menu items) -- page base 0x02e92c18, 102 rows */
static const fx6_menu_row_t fx6_paint_overlay_page_rows[] = {
    {"No142_BLOCK_TOUCH", 0x042d5860u, {0,0,1024,540}, 0x00000000u, 0},
    {"No144_BG", 0x042d5a50u, {56,49,912,477}, 0x020001d2u, 0},
    {"No141_TEXT_INPUT_TOUCH", 0x042d5970u, {60,118,902,62}, 0x00000000u, 0},
    {"No16_TEXT_BOX", 0x042d5a40u, {75,119,874,60}, 0x0200c005u, 0},
    {"No17_TEXT_BOX", 0x042d5a40u, {76,120,872,58}, 0x0200c009u, 0},
    {"No18_TEXT_INPUT", 0x042d57f0u, {60,128,904,42}, 0x00000000u, 0},
    {"No15_TITLE", 0x042d57f0u, {516,54,405,36}, 0x02004c67u, 0},
    {"No146_TITLE_PARENT", 0x042d57f0u, {97,53,405,36}, 0x00000000u, 0},
    {"No143_CANCEL_BG", 0x042d58d0u, {574,454,182,52}, 0x020056e8u, 0},
    {"No103_DONE_BG", 0x042d58d0u, {766,454,182,52}, 0x02004c6fu, 0},
    {"No36_SYMBOL", 0x042d58d0u, {484,200,126,52}, 0x02004c6cu, 0},
    {"No31_NUMERIC", 0x042d58d0u, {348,200,126,52}, 0x02004cbeu, 0},
    {"No26_LOWER_ALPHABET", 0x042d58d0u, {212,200,126,52}, 0x02004c6bu, 0},
    {"No21_UPPER_ALPHABET", 0x042d58d0u, {76,200,126,52}, 0x02004c6au, 0},
    {"No98_RIGHTARROW_BG", 0x042d58d0u, {244,454,64,52}, 0x00000000u, 0},
    {"No95_LEFTARROW_BG", 0x042d58d0u, {170,454,64,52}, 0x00000000u, 0},
    {"No93_SPACE_BG", 0x042d58d0u, {76,454,64,52}, 0x00000000u, 0},
    {"No148_MASK_DISP_SWITCH_BUTTON", 0x042d58d0u, {884,200,64,52}, 0x00000000u, 0},
    {"No101_BACKSPACE_BG", 0x042d58d0u, {338,454,64,52}, 0x00000000u, 0},
    {"No41_KEY_Z", 0x042d58d0u, {885,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_Y", 0x042d58d0u, {819,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_X", 0x042d58d0u, {753,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_W", 0x042d58d0u, {687,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_V", 0x042d58d0u, {621,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_U", 0x042d58d0u, {555,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_T", 0x042d58d0u, {489,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_S", 0x042d58d0u, {423,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_R", 0x042d58d0u, {357,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_Q", 0x042d58d0u, {291,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_P", 0x042d58d0u, {225,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_O", 0x042d58d0u, {159,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_N", 0x042d58d0u, {93,362,46,46}, 0x00000000u, 0},
    {"No41_KEY_M", 0x042d58d0u, {885,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_L", 0x042d58d0u, {819,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_K", 0x042d58d0u, {753,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_J", 0x042d58d0u, {687,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_I", 0x042d58d0u, {621,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_H", 0x042d58d0u, {555,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_G", 0x042d58d0u, {489,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_F", 0x042d58d0u, {423,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_E", 0x042d58d0u, {357,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_D", 0x042d58d0u, {291,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_C", 0x042d58d0u, {225,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_B", 0x042d58d0u, {159,284,46,46}, 0x00000000u, 0},
    {"No41_KEY_A", 0x042d58d0u, {93,284,46,46}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_9", 0x042d57f0u, {339,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_8", 0x042d57f0u, {308,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_7", 0x042d57f0u, {277,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_6", 0x042d57f0u, {246,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_5", 0x042d57f0u, {215,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_4", 0x042d57f0u, {184,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_3", 0x042d57f0u, {153,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_27", 0x042d57f0u, {897,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_26", 0x042d57f0u, {866,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_25", 0x042d57f0u, {835,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_24", 0x042d57f0u, {804,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_23", 0x042d57f0u, {773,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_22", 0x042d57f0u, {742,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_21", 0x042d57f0u, {711,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_20", 0x042d57f0u, {680,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_2", 0x042d57f0u, {122,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_19", 0x042d57f0u, {649,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_18", 0x042d57f0u, {618,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_17", 0x042d57f0u, {587,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_16", 0x042d57f0u, {556,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_15", 0x042d57f0u, {525,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_14", 0x042d57f0u, {494,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_13", 0x042d57f0u, {463,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_12", 0x042d57f0u, {432,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_11", 0x042d57f0u, {401,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_10", 0x042d57f0u, {370,128,31,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_CHAR_1", 0x042d57f0u, {91,128,31,40}, 0x00000000u, 0},
    {"No147_MENUICON", 0x042d5a50u, {61,54,34,34}, 0x02000043u, 0},
    {"No19_TEXT_INPUT_MASK_LEFT", 0x042d5a50u, {76,134,31,32}, 0x0200020du, 0},
    {"No140_TEXT_BOX_CHAR_0", 0x042d57f0u, {76,128,8,40}, 0x00000000u, 0},
    {"No140_TEXT_BOX_INPUT_POS_9", 0x042d5a40u, {337,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_8", 0x042d5a40u, {306,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_7", 0x042d5a40u, {275,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_6", 0x042d5a40u, {244,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_5", 0x042d5a40u, {213,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_4", 0x042d5a40u, {182,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_3", 0x042d5a40u, {151,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_27", 0x042d5a40u, {895,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_26", 0x042d5a40u, {864,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_25", 0x042d5a40u, {833,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_24", 0x042d5a40u, {802,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_23", 0x042d5a40u, {771,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_22", 0x042d5a40u, {740,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_21", 0x042d5a40u, {709,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_20", 0x042d5a40u, {678,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_2", 0x042d5a40u, {120,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_19", 0x042d5a40u, {647,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_18", 0x042d5a40u, {616,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_17", 0x042d5a40u, {585,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_16", 0x042d5a40u, {554,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_15", 0x042d5a40u, {523,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_14", 0x042d5a40u, {492,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_13", 0x042d5a40u, {461,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_12", 0x042d5a40u, {430,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_11", 0x042d5a40u, {399,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_10", 0x042d5a40u, {368,128,2,40}, 0x0200c014u, 0},
    {"No140_TEXT_BOX_INPUT_POS_1", 0x042d5a40u, {89,128,2,40}, 0x0200c014u, 0},
};
#define FX6_PAINT_OVERLAY_PAGE_ROWS_COUNT (sizeof(fx6_paint_overlay_page_rows)/sizeof(fx6_paint_overlay_page_rows[0]))

/* Media format / confirm page -- page base 0x02eafdd8, 49 rows */
static const fx6_menu_row_t fx6_media_format_confirm_rows[] = {
    {"No49_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1_Backgroundleft", 0x042d5a40u, {56,49,482,477}, 0x0200c006u, 0},
    {"No13_Backgroundright", 0x042d5a40u, {542,49,426,477}, 0x0200c006u, 0},
    {"No38_Gridlist", 0x042d59e0u, {126,102,403,415}, 0x00000000u, 0},
    {"No48_itemtouchbutton10", 0x042d58d0u, {546,493,418,44}, 0x00000000u, 0},
    {"No47_itemtouchbutton9", 0x042d58d0u, {546,449,418,44}, 0x00000000u, 0},
    {"No46_itemtouchbutton8", 0x042d58d0u, {546,405,418,44}, 0x00000000u, 0},
    {"No45_itemtouchbutton7", 0x042d58d0u, {546,361,418,44}, 0x00000000u, 0},
    {"No44_itemtouchbutton6", 0x042d58d0u, {546,317,418,44}, 0x00000000u, 0},
    {"No43_itemtouchbutton5", 0x042d58d0u, {546,273,418,44}, 0x00000000u, 0},
    {"No42_itemtouchbutton4", 0x042d58d0u, {546,229,418,44}, 0x00000000u, 0},
    {"No41_itemtouchbutton3", 0x042d58d0u, {546,185,418,44}, 0x00000000u, 0},
    {"No40_itemtouchbutton2", 0x042d58d0u, {546,141,418,44}, 0x00000000u, 0},
    {"No39_itemtouchbutton1", 0x042d58d0u, {546,97,418,44}, 0x00000000u, 0},
    {"No14_Backgroundthesecondlayeritem", 0x042d5a40u, {545,52,420,41}, 0x0200c009u, 0},
    {"No4_ItemBG", 0x042d5a40u, {126,62,401,36}, 0x0200c00du, 0},
    {"No36_Itemselectionofthesecondlayer", 0x042d57f0u, {548,54,330,36}, 0x00000000u, 0},
    {"No6_Itemselectionofthefirstlayer", 0x042d57f0u, {128,62,280,36}, 0x02004d4au, 0},
    {"No34_item10inthethirdlayer", 0x042d57f0u, {551,497,254,36}, 0x00000000u, 0},
    {"No33_item9inthethirdlayer", 0x042d57f0u, {551,453,254,36}, 0x00000000u, 0},
    {"No32_item8inthethirdlayer", 0x042d57f0u, {551,409,254,36}, 0x00000000u, 0},
    {"No31_item7inthethirdlayer", 0x042d57f0u, {551,365,254,36}, 0x00000000u, 0},
    {"No30_item6inthethirdlayer", 0x042d57f0u, {551,321,254,36}, 0x00000000u, 0},
    {"No29_item5inthethirdlayer", 0x042d57f0u, {551,277,254,36}, 0x00000000u, 0},
    {"No28_item4inthethirdlayer", 0x042d57f0u, {551,233,254,36}, 0x00000000u, 0},
    {"No27_item3inthethirdlayer", 0x042d57f0u, {551,189,254,36}, 0x00000000u, 0},
    {"No26_item2inthethirdlayer", 0x042d57f0u, {551,145,254,36}, 0x00000000u, 0},
    {"No25_item1inthethirdlayer", 0x042d57f0u, {551,101,254,36}, 0x00000000u, 0},
    {"No35_Thirdlayershadow", 0x042d5a50u, {545,503,420,20}, 0x020001a8u, 0},
    {"No5_TabnumberBG", 0x042d5a40u, {443,66,80,28}, 0x0200c00fu, 0},
    {"No37_Tabnumber", 0x042d57f0u, {444,66,78,30}, 0x00000000u, 0},
    {"No16_Secondlayeritemshadow2", 0x042d5a50u, {545,93,420,4}, 0x02000003u, 0},
    {"No12_Lowerleftoutsideline2", 0x042d5a40u, {57,525,481,2}, 0x0200c009u, 0},
    {"No10_Upperleftoutsideline2", 0x042d5a40u, {57,50,481,2}, 0x0200c00au, 0},
    {"No11_Lowerleftoutsideline", 0x042d5a40u, {57,523,479,2}, 0x0200c005u, 0},
    {"No8_Leftoutsideline2", 0x042d5a40u, {57,50,2,473}, 0x0200c00au, 0},
    {"No24_Rightoutsideline2", 0x042d5a40u, {967,50,2,473}, 0x0200c00au, 0},
    {"No18_Leftoutsideline2", 0x042d5a40u, {543,50,2,473}, 0x0200c00au, 0},
    {"No3_Separator2", 0x042d5a40u, {124,52,2,471}, 0x0200c00eu, 0},
    {"No2_Separator", 0x042d5a40u, {122,52,2,471}, 0x0200c001u, 0},
    {"No22_Lowerrigntoutsideline2", 0x042d5a40u, {543,525,425,2}, 0x0200c009u, 0},
    {"No21_Lowerrigntoutsideline", 0x042d5a40u, {543,523,424,2}, 0x0200c005u, 0},
    {"No20_Upperrigntoutsideline2", 0x042d5a40u, {544,50,424,2}, 0x0200c00au, 0},
    {"No9_Upperleftoutsideline", 0x042d5a40u, {57,49,479,1}, 0x0200c009u, 0},
    {"No7_Leftoutsideline", 0x042d5a40u, {56,49,1,477}, 0x0200c009u, 0},
    {"No23_Rightoutsideline", 0x042d5a40u, {965,49,1,477}, 0x0200c009u, 0},
    {"No17_Leftoutsideline", 0x042d5a40u, {542,49,1,477}, 0x0200c009u, 0},
    {"No19_Upperrigntoutsideline", 0x042d5a40u, {542,49,424,1}, 0x0200c009u, 0},
    {"No15_Secondlayeritemshadow1", 0x042d5a40u, {545,92,420,1}, 0x0200c00bu, 0},
};
#define FX6_MEDIA_FORMAT_CONFIRM_ROWS_COUNT (sizeof(fx6_media_format_confirm_rows)/sizeof(fx6_media_format_confirm_rows[0]))

/* Playback control page -- page base 0x02eb1890, 54 rows */
static const fx6_menu_row_t fx6_playback_control_rows[] = {
    {"No45_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No4_PANEL_BG", 0x042d5a40u, {56,49,912,477}, 0x0200c003u, 0},
    {"No38_SEPARATOR", 0x042d5a40u, {59,449,906,2}, 0x0200c00bu, 0},
    {"No37_SEPARATOR", 0x042d5a40u, {59,369,906,2}, 0x0200c00bu, 0},
    {"No36_SEPARATOR", 0x042d5a40u, {59,289,906,2}, 0x0200c00bu, 0},
    {"No35_SEPARATOR", 0x042d5a40u, {59,209,906,2}, 0x0200c00bu, 0},
    {"No34_SEPARATOR", 0x042d5a40u, {59,129,906,2}, 0x0200c00bu, 0},
    {"No33_SEPARATOR", 0x042d5a40u, {59,94,906,2}, 0x0200c00bu, 0},
    {"No41_SEPARATOR", 0x042d5a40u, {690,129,2,396}, 0x0200c00bu, 0},
    {"No59_SEPARATOR", 0x042d5a40u, {690,290,2,236}, 0x0200c00bu, 0},
    {"No40_SEPARATOR", 0x042d5a40u, {500,129,2,160}, 0x0200c00bu, 0},
    {"No39_SEPARATOR", 0x042d5a40u, {170,129,2,160}, 0x0200c00bu, 0},
    {"No16_TOUCHBUTTON_SDIHDMI_SIGNAL", 0x042d58d0u, {174,132,324,156}, 0x00000000u, 0},
    {"No43_TOUCHBUTTON_BASE_LOOK_LUT", 0x042d58d0u, {60,452,628,70}, 0x00000000u, 0},
    {"No28_TOUCHBUTTON_STREAMVF_GAMUT", 0x042d58d0u, {694,292,268,156}, 0x00000000u, 0},
    {"No25_TOUCHBUTTON_SDIHDMI_GAMUT", 0x042d58d0u, {694,132,268,156}, 0x00000000u, 0},
    {"No66_TOUCH_BUTTON_LEFT_ARROW", 0x042d58d0u, {0,50,56,475}, 0x00000000u, 0},
    {"No61_STREAM_SIGNAL_BUTTON", 0x042d58d0u, {174,292,324,76}, 0x00000000u, 0},
    {"No67_TOUCHBUTTON_LCD_VF_GAMUT", 0x042d58d0u, {694,372,268,76}, 0x00000000u, 0},
    {"No30_TOUCHBUTTON_GAMMA_DISP", 0x042d58d0u, {694,452,268,70}, 0x00000000u, 0},
    {"No31_TOUCHBUTTON_TITLE", 0x042d57f0u, {106,54,405,36}, 0x0200211du, 0},
    {"No20_TOUCHBUTTON_HDMI_INFODISP", 0x042d58d0u, {504,212,184,76}, 0x00000000u, 0},
    {"No19_TOUCHBUTTON_SDI_INFODISP", 0x042d58d0u, {504,132,184,76}, 0x00000000u, 0},
    {"No49_LABEL_HDMI_SIGNAL", 0x042d57f0u, {182,232,310,36}, 0x00000000u, 0},
    {"No48_LABEL_SDI_SIGNAL", 0x042d57f0u, {182,152,310,36}, 0x00000000u, 0},
    {"No7_LABEL_SIGNAL_TITLE", 0x042d57f0u, {174,97,310,30}, 0x020021b6u, 0},
    {"No53_LABEL_LCD_VF_GAMUT", 0x042d57f0u, {746,392,210,36}, 0x00000000u, 0},
    {"No52_LABEL_STREAM_GAMUT", 0x042d57f0u, {746,312,210,36}, 0x00000000u, 0},
    {"No51_LABEL_HDMI_GAMUT", 0x042d57f0u, {746,232,210,36}, 0x00000000u, 0},
    {"No50_LABEL_SDI_GAMUT", 0x042d57f0u, {746,152,210,36}, 0x00000000u, 0},
    {"No44_PAGE_BUTTON", 0x042d58d0u, {802,52,164,40}, 0x00000000u, 0},
    {"No9_LABEL_GAMUT_TITLE", 0x042d57f0u, {694,97,210,30}, 0x02002036u, 0},
    {"No47_LABEL_VF_NOINFO", 0x042d57f0u, {512,392,170,36}, 0x020050f6u, 0},
    {"No46_LABEL_STREAM_OFF", 0x042d57f0u, {512,312,170,36}, 0x020056f0u, 0},
    {"No63_INDEX_BUTTON", 0x042d58d0u, {668,52,132,40}, 0x00000000u, 0},
    {"No8_LABEL_INFODISP_TITLE", 0x042d57f0u, {504,97,170,30}, 0x020051a8u, 0},
    {"No6_PAGE_NUMBER", 0x042d57f0u, {852,54,110,36}, 0x00000000u, 0},
    {"No58_INTERLOCK_STREAM_VF", 0x042d5a50u, {702,312,38,102}, 0x02000437u, 0},
    {"No65_INDEX_STRING", 0x042d57f0u, {706,54,94,36}, 0x02002e12u, 0},
    {"No57_INTERLOCK_SDI_HDMI", 0x042d5a50u, {702,166,38,88}, 0x02000438u, 0},
    {"No13_LABEL_VF_TITLE", 0x042d57f0u, {68,395,96,30}, 0x02002b0du, 0},
    {"No12_LABEL_STREAM_TITLE", 0x042d57f0u, {68,315,96,30}, 0x0200219au, 0},
    {"No11_LABEL_HDMI_TITLE", 0x042d57f0u, {68,235,96,30}, 0x0200516au, 0},
    {"No10_LABEL_SDI_TITLE", 0x042d57f0u, {68,155,96,30}, 0x020044cdu, 0},
    {"No62_LEFT_ARROW", 0x042d5a50u, {32,267,45,60}, 0x0200043du, 0},
    {"No60_TITLE_ICON", 0x042d57f0u, {60,51,45,42}, 0x020026c5u, 0},
    {"No64_INDEX_ARROW", 0x042d57f0u, {668,54,38,36}, 0x02002e21u, 0},
    {"No70_ASSIGNABLE_NUMBER_1_LOWER", 0x042d5a50u, {702,232,36,36}, 0x02000440u, 0},
    {"No69_ASSIGNABLE_NUMBER_2", 0x042d5a50u, {702,392,36,36}, 0x0200043fu, 0},
    {"No68_ASSIGNABLE_NUMBER_1_UPPER", 0x042d5a50u, {702,152,36,36}, 0x02000440u, 0},
    {"No42_PAGE_SCROLL_ARROW", 0x042d57f0u, {814,54,36,36}, 0x020021d6u, 0},
    {"No56_HIGHLIGHT_SDI_HDMI", 0x042d57d0u, {56,132,906,156}, 0x00000000u, 0},
    {"No55_HIGHLIGHT_HDMI", 0x042d57d0u, {56,212,906,76}, 0x00000000u, 0},
    {"No54_HIGHLIGHT_SDI", 0x042d57d0u, {56,132,906,76}, 0x00000000u, 0},
};
#define FX6_PLAYBACK_CONTROL_ROWS_COUNT (sizeof(fx6_playback_control_rows)/sizeof(fx6_playback_control_rows[0]))

/* Two-column item grid page (18 menu items) -- page base 0x02eac280, 34 rows */
static const fx6_menu_row_t fx6_menu_grid_page_rows[] = {
    {"No26_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1_BG", 0x042d5a40u, {56,49,912,477}, 0x0200c003u, 0},
    {"No34_TOUCH_BUTTON_LEFT_ARROW", 0x042d58d0u, {0,50,56,475}, 0x00000000u, 0},
    {"No9_BUTTON_06", 0x042d58d0u, {364,97,298,82}, 0x00000000u, 0},
    {"No8_BUTTON_05", 0x042d58d0u, {60,441,298,82}, 0x00000000u, 0},
    {"No7_BUTTON_04", 0x042d58d0u, {60,355,298,82}, 0x00000000u, 0},
    {"No6_BUTTON_03", 0x042d58d0u, {60,269,298,82}, 0x00000000u, 0},
    {"No5_BUTTON_02", 0x042d58d0u, {60,183,298,82}, 0x00000000u, 0},
    {"No4_BUTTON_01", 0x042d58d0u, {60,97,298,82}, 0x00000000u, 0},
    {"No18_BUTTON_15", 0x042d58d0u, {668,441,298,82}, 0x00000000u, 0},
    {"No17_BUTTON_14", 0x042d58d0u, {668,355,298,82}, 0x00000000u, 0},
    {"No16_BUTTON_13", 0x042d58d0u, {668,269,298,82}, 0x00000000u, 0},
    {"No15_BUTTON_12", 0x042d58d0u, {668,183,298,82}, 0x00000000u, 0},
    {"No14_BUTTON_11", 0x042d58d0u, {668,97,298,82}, 0x00000000u, 0},
    {"No13_BUTTON_10", 0x042d58d0u, {364,441,298,82}, 0x00000000u, 0},
    {"No12_BUTTON_09", 0x042d58d0u, {364,355,298,82}, 0x00000000u, 0},
    {"No11_BUTTON_08", 0x042d58d0u, {364,269,298,82}, 0x00000000u, 0},
    {"No10_BUTTON_07", 0x042d58d0u, {364,183,298,82}, 0x00000000u, 0},
    {"No3_TITLE", 0x042d57f0u, {106,54,405,36}, 0x0200211au, 0},
    {"No27_PAGE_BUTTON", 0x042d58d0u, {802,52,164,40}, 0x00000000u, 0},
    {"No31_INDEX_BUTTON", 0x042d58d0u, {668,52,132,40}, 0x00000000u, 0},
    {"No2_PAGE_NUMBER", 0x042d57f0u, {852,54,110,36}, 0x00000000u, 0},
    {"No33_INDEX_STRING", 0x042d57f0u, {706,54,94,36}, 0x02002e12u, 0},
    {"No30_LEFT_ARROW", 0x042d5a50u, {32,267,45,60}, 0x0200043du, 0},
    {"No29_TITLE_ICON", 0x042d57f0u, {60,51,45,42}, 0x020026c1u, 0},
    {"No23_SEPARATOR", 0x042d5a40u, {59,438,906,2}, 0x0200c00bu, 0},
    {"No22_SEPARATOR", 0x042d5a40u, {59,352,906,2}, 0x0200c00bu, 0},
    {"No21_SEPARATOR", 0x042d5a40u, {59,266,906,2}, 0x0200c00bu, 0},
    {"No20_SEPARATOR", 0x042d5a40u, {59,180,906,2}, 0x0200c00bu, 0},
    {"No19_SEPARATOR", 0x042d5a40u, {59,94,906,2}, 0x0200c00bu, 0},
    {"No32_INDEX_ARROW", 0x042d57f0u, {668,54,38,36}, 0x02002e21u, 0},
    {"No28_PAGE_ARROW", 0x042d57f0u, {814,54,36,36}, 0x020021d6u, 0},
    {"No25_SEPARATOR", 0x042d5a40u, {664,94,2,430}, 0x0200c00bu, 0},
    {"No24_SEPARATOR", 0x042d5a40u, {360,94,2,430}, 0x0200c00bu, 0},
};
#define FX6_MENU_GRID_PAGE_ROWS_COUNT (sizeof(fx6_menu_grid_page_rows)/sizeof(fx6_menu_grid_page_rows[0]))

/* Two-column item grid page variant -- page base 0x02ea4990, 33 rows */
static const fx6_menu_row_t fx6_menu_grid_page2_rows[] = {
    {"No26_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1_BG", 0x042d5a40u, {56,49,912,477}, 0x0200c003u, 0},
    {"No33_TOUCH_BUTTON_LEFT_ARROW", 0x042d58d0u, {0,50,56,475}, 0x00000000u, 0},
    {"No9_BUTTON_06", 0x042d58d0u, {364,97,298,82}, 0x00000000u, 0},
    {"No8_BUTTON_05", 0x042d58d0u, {60,441,298,82}, 0x00000000u, 0},
    {"No7_BUTTON_04", 0x042d58d0u, {60,355,298,82}, 0x00000000u, 0},
    {"No6_BUTTON_03", 0x042d58d0u, {60,269,298,82}, 0x00000000u, 0},
    {"No5_BUTTON_02", 0x042d58d0u, {60,183,298,82}, 0x00000000u, 0},
    {"No4_BUTTON_01", 0x042d58d0u, {60,97,298,82}, 0x00000000u, 0},
    {"No18_BUTTON_15", 0x042d58d0u, {668,441,298,82}, 0x00000000u, 0},
    {"No17_BUTTON_14", 0x042d58d0u, {668,355,298,82}, 0x00000000u, 0},
    {"No16_BUTTON_13", 0x042d58d0u, {668,269,298,82}, 0x00000000u, 0},
    {"No15_BUTTON_12", 0x042d58d0u, {668,183,298,82}, 0x00000000u, 0},
    {"No14_BUTTON_11", 0x042d58d0u, {668,97,298,82}, 0x00000000u, 0},
    {"No13_BUTTON_10", 0x042d58d0u, {364,441,298,82}, 0x00000000u, 0},
    {"No12_BUTTON_09", 0x042d58d0u, {364,355,298,82}, 0x00000000u, 0},
    {"No11_BUTTON_08", 0x042d58d0u, {364,269,298,82}, 0x00000000u, 0},
    {"No10_BUTTON_07", 0x042d58d0u, {364,183,298,82}, 0x00000000u, 0},
    {"No3_TITLE", 0x042d57f0u, {62,54,405,36}, 0x020024ceu, 0},
    {"No27_PAGE_BUTTON", 0x042d58d0u, {802,52,164,40}, 0x00000000u, 0},
    {"No30_INDEX_BUTTON", 0x042d58d0u, {668,52,132,40}, 0x00000000u, 0},
    {"No2_PAGE_NUMBER", 0x042d57f0u, {852,54,110,36}, 0x00000000u, 0},
    {"No32_INDEX_STRING", 0x042d57f0u, {706,54,94,36}, 0x02002e12u, 0},
    {"No29_LEFT_ARROW", 0x042d5a50u, {32,267,45,60}, 0x0200043du, 0},
    {"No23_SEPARATOR", 0x042d5a40u, {59,438,906,2}, 0x0200c00bu, 0},
    {"No22_SEPARATOR", 0x042d5a40u, {59,352,906,2}, 0x0200c00bu, 0},
    {"No21_SEPARATOR", 0x042d5a40u, {59,266,906,2}, 0x0200c00bu, 0},
    {"No20_SEPARATOR", 0x042d5a40u, {59,180,906,2}, 0x0200c00bu, 0},
    {"No19_SEPARATOR", 0x042d5a40u, {59,94,906,2}, 0x0200c00bu, 0},
    {"No31_INDEX_ARROW", 0x042d57f0u, {668,54,38,36}, 0x02002e21u, 0},
    {"No28_PAGE_ARROW", 0x042d57f0u, {814,54,36,36}, 0x020021d6u, 0},
    {"No25_SEPARATOR", 0x042d5a40u, {664,94,2,430}, 0x0200c00bu, 0},
    {"No24_SEPARATOR", 0x042d5a40u, {360,94,2,430}, 0x0200c00bu, 0},
};
#define FX6_MENU_GRID_PAGE2_ROWS_COUNT (sizeof(fx6_menu_grid_page2_rows)/sizeof(fx6_menu_grid_page2_rows[0]))

/* Settings sub page (12 menu items) -- page base 0x02eb0d08, 28 rows */
static const fx6_menu_row_t fx6_settings_sub_page_rows[] = {
    {"No25_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No1_BG", 0x042d5a40u, {56,49,912,477}, 0x0200c003u, 0},
    {"No6_BUTTON_03", 0x042d58d0u, {60,269,904,82}, 0x00000000u, 0},
    {"No9_BUTTON_06", 0x042d58d0u, {515,97,449,82}, 0x00000000u, 0},
    {"No8_BUTTON_05", 0x042d58d0u, {60,441,449,82}, 0x00000000u, 0},
    {"No7_BUTTON_04", 0x042d58d0u, {60,355,449,82}, 0x00000000u, 0},
    {"No5_BUTTON_02", 0x042d58d0u, {60,183,449,82}, 0x00000000u, 0},
    {"No4_BUTTON_01", 0x042d58d0u, {60,97,449,82}, 0x00000000u, 0},
    {"No13_BUTTON_09", 0x042d58d0u, {515,441,449,82}, 0x00000000u, 0},
    {"No12_BUTTON_08", 0x042d58d0u, {515,355,449,82}, 0x00000000u, 0},
    {"No10_BUTTON_07", 0x042d58d0u, {515,183,449,82}, 0x00000000u, 0},
    {"No33_TOUCH_BUTTON_LEFT_ARROW", 0x042d58d0u, {0,50,56,475}, 0x00000000u, 0},
    {"No3_TITLE", 0x042d57f0u, {106,54,405,36}, 0x02002bd4u, 0},
    {"No27_PAGE_BUTTON", 0x042d58d0u, {802,52,164,40}, 0x00000000u, 0},
    {"No30_INDEX_BUTTON", 0x042d58d0u, {668,52,132,40}, 0x00000000u, 0},
    {"No2_PAGE_NUMBER", 0x042d57f0u, {852,54,110,36}, 0x00000000u, 0},
    {"No32_INDEX_STRING", 0x042d57f0u, {706,54,94,36}, 0x02002e12u, 0},
    {"No29_LEFT_ARROW", 0x042d5a50u, {32,267,45,60}, 0x0200043du, 0},
    {"No28_TITLE_ICON", 0x042d57f0u, {60,51,45,42}, 0x02002c4du, 0},
    {"No22_SEPARATOR", 0x042d5a40u, {59,438,906,2}, 0x0200c00bu, 0},
    {"No21_SEPARATOR", 0x042d5a40u, {59,352,906,2}, 0x0200c00bu, 0},
    {"No20_SEPARATOR", 0x042d5a40u, {59,266,906,2}, 0x0200c00bu, 0},
    {"No18_SEPARATOR", 0x042d5a40u, {59,180,906,2}, 0x0200c00bu, 0},
    {"No17_SEPARATOR", 0x042d5a40u, {59,94,906,2}, 0x0200c00bu, 0},
    {"No31_INDEX_ARROW", 0x042d57f0u, {668,54,38,36}, 0x02002e21u, 0},
    {"No24_PAGE_SCROLL_ARROW", 0x042d57f0u, {814,54,36,36}, 0x020021d6u, 0},
    {"No26_SEPARATOR", 0x042d5a40u, {511,352,2,172}, 0x0200c00bu, 0},
    {"No23_SEPARATOR", 0x042d5a40u, {511,94,2,172}, 0x0200c00bu, 0},
};
#define FX6_SETTINGS_SUB_PAGE_ROWS_COUNT (sizeof(fx6_settings_sub_page_rows)/sizeof(fx6_settings_sub_page_rows[0]))

/* Toast / confirm page -- page base 0x02e9deb0, 11 rows */
static const fx6_menu_row_t fx6_toast_confirm_page_rows[] = {
    {"No17_TOUCH_SCREEN", 0x042d5970u, {0,0,1024,540}, 0x00000000u, 0},
    {"No2_BG", 0x042d5a50u, {56,49,912,477}, 0x020001d2u, 0},
    {"No16_LIST", 0x042d59e0u, {64,200,902,314}, 0x00000000u, 0},
    {"No15_BACK", 0x042d5850u, {64,100,892,58}, 0x00000000u, 0},
    {"No4_TITLE", 0x042d57f0u, {62,53,420,38}, 0x02004383u, 0},
    {"No12_CLIPNAME", 0x042d57f0u, {140,171,292,30}, 0x02004391u, 0},
    {"No14_STATUS", 0x042d57f0u, {698,171,250,30}, 0x02004393u, 0},
    {"No13_DESTINATION", 0x042d57f0u, {452,171,250,30}, 0x02004392u, 0},
    {"No3_TOTALNUM", 0x042d57f0u, {822,54,140,36}, 0x02004c3bu, 0},
    {"No11_SRCMEDIA", 0x042d57f0u, {72,171,60,30}, 0x02004390u, 0},
    {"No10_LINE_P", 0x042d5a50u, {64,162,892,2}, 0x020001fau, 0},
};
#define FX6_TOAST_CONFIRM_PAGE_ROWS_COUNT (sizeof(fx6_toast_confirm_page_rows)/sizeof(fx6_toast_confirm_page_rows[0]))

