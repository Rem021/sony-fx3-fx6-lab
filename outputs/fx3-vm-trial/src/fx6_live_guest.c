/* fx6_live_guest.c — Interactive in-guest FX6 native UI controller & renderer
 *
 * Runs inside the ARM64 QEMU guest on AppFw UI thread (tid 222) via fx6_force_update().
 * Renders 100% authentic FX6 pages using real /usr/lib/appFw.so + /usr/lib/libuxengine.so
 * + TextRM + ResourceManager into physical framebuffer 0x41e001000 (gpe0, 1024x540x4).
 *
 * Mailboxes:
 *   0x41df00000: SRM3KYE5 hardware key mailbox (k32[2]=seq, k32[3]=key, k32[6]=ack)
 *   0x41e000e00: FX6L state/page control mailbox (osd41e + 0x0e00):
 *     mb[0] = 0x4658364c ('FX6L')
 *     mb[1] = cmd_seq (incremented by host or guest key handler)
 *     mb[2] = ack_seq (written by guest AFTER gpe0 frame is completely rendered)
 *     mb[3] = page (0..23 curated FX6 UI pages, 24=Universal 128-Page Descriptor Table Mode)
 *     mb[4] = sel_box (active widget/button/row/cell cursor index)
 *     mb[5] = menu_cat (0..10 for the 11 Three-Layer Menu categories)
 *     mb[6] = menu_item (0..N-1 item index in right column)
 *     mb[7] = menu_depth (0=left category column, 1=right item list, 2=3rd-layer / subpage variant)
 *     mb[8..13] = cell_val[0..5] (FPS, EI/BaseISO, Shutter, ND[P4-Locked], LUT, WB; or Page 24 table specs)
 *     mb[14] = rec_fmt_idx (0..4 Rec Format option index)
 *     mb[15] = stats ((text_ok << 24) | (nonzero_pixels & 0x00ffffff))
 *     mb[16] = lang_id (0=English/bank4, 1=Simplified Chinese/bank19, 2=Japanese/bank12)
 *     mb[17] = fx3_p10_hwcode telemetry ((phy_code << 16) | infra_code)
 *     mb[18] = cinema_p11_state ((xlr_idx << 4) | ibis_idx) for P11 XLR-H1 & 5-axis IBIS lock
 *     mb[19] = lut_tint_meta ((user_slot_1to4 << 28) | (valid << 24) | (r << 16) | (g << 8) | b)
 *     mb[20..25] = active User LUT short name (24 bytes NUL-terminated)
 *     mb[26] = audio_db_packed (4x uint8_t (db + 60) for ch1..ch4 in [-60..+12])
 *     mb[27] = phase40+phase56_flags (bit0=xlr_attached, bit1=+48V, bits4..5=rtmd_ibis,
 *              bit8=bk4_locked, bit9=phase40_valid, bits12..14=aspect_marker,
 *              bits16..17=zebra_mode, bits18..19=peaking_mode, bits20..21=desqueeze,
 *              bit24=phase56_valid)
 *     mb[28] = phase64_flags (bit0=base12800, bits1..4=ei_step(0..12), bits5..6=shutter_mode,
 *              bit7=sq_enabled, bits8..10=base_fps_idx, bit11=rec_on, bits12..13=tally_mode,
 *              bits14..15=wired_io_mode, bit16=p4_nd_absent, bit17=p12_rf_off, bit31=valid)
 *     mb[29] = phase64_shutter_sq (bits0..19=shutter_val, bits20..27=sq_fps(1..240))
 *     mb[30] = phase64_tc_frames (live TC frame counter when REC)
 *     mb[31] = 0x43494e45 ('CINE') Phase 64 CINE_EXP magic tag
 *     mb[32] = phase73_wb_look (bits0..2=wb_mode, bits3..16=kelvin, bits17..24=tint+99,
 *              bits25..26=shockless_wb, bits27..29=base_look, bit30=fx3_wb_soft_mapped, bit31=valid)
 *     mb[33] = phase73_media_clip (bits0..4=cam_id, bits5..14=reel_num, bits15..16=cam_pos,
 *              bits17..26=clip_seq, bits27..28=dual_slot_mode, bits29..30=proxy_mode, bit31=proxy_eff)
 *     mb[34] = phase73_flags2 (bit0=proxy_auto_suspended_by_sq, bits1..3=user_lut_slot_1to4)
 *     mb[35] = 0x57424c4d ('WBLM') Phase 73 WB_MEDIA magic tag
 *     mb[36] = phase81_touch_af (bits0..1=touch_af_mode(0=off,1=focus,2=tracking),
 *              bits2..11=touch_x(0..959), bits12..21=touch_y(0..539), bits22..31=pdaf_index(0..626))
 *     mb[37] = phase81_pdaf_mag_fc (bits0..5=pdaf_col(0..32), bits6..10=pdaf_row(0..18),
 *              bits11..12=focus_mag(0=1x,1=2x,2=4x), bits13..14=false_color(0=off,1=slog3_ire,2=el_zone),
 *              bit15=clean_hdmi_unmagnified, bits16..23=eff_ciz_x100(100..200), bits24..31=req_ciz_x100(100..200))
 *     mb[38] = phase81_ciz_flags (bits0..3=rocker_speed(1..8), bit4=ciz_res_fhd,
 *              bit5=ciz_clamped_by_exclusion, bit6=ciz_clamped_by_res_limit,
 *              bit7=slog3_zebra100_clip_warning, bit8=letterbox_ignored, bit31=valid)
 *     mb[39] = 0x54414643 ('TAFC') Phase 81 Touch-AF / False-Color / CIZ magic tag
 *     mb[40] = phase88_shotmark (bits0..6=total_count(0..64), bits7..13=m1_count,
 *              bits14..20=m2_count, bits21..22=last_type(0=none,1=M1,2=M2), bits23..31=last_frame_low)
 *     mb[41] = phase88_iris_audio (bits0..11=iris_x100(140..2200), bits12..13=metering(0=multi,1=center,2=spot,3=highlight),
 *              bits14..21=ae_shift_enc((ev+2.0)*8), bit22=ch34_pad_20db, bit23=push_auto_iris_active,
 *              bits24..30=target_ire(41), bit31=valid)
 *     mb[42] = phase88_user_bits (SMPTE 12M 32-bit User-Bits e.g. 0xA0010001)
 *     mb[43] = 0x534d524b ('SMRK') Phase 88 ShotMark / Push Auto Iris / Safety Audio magic tag
 *     mb[44] = phase95_anamorphic_ibis (bits0..2=squeeze_idx(0..5), bits3..5=eff_ibis_idx(0..4),
 *              bits6..8=req_ibis_idx(0..4), bit9=ibis_arbitrated, bit10=center_lock_0x0400,
 *              bits11..18=yaw_gain_pct(0..100), bits19..28=synced_touch_x(0..959),
 *              bit29=desqueeze_touch_synced, bit30=edge_wobble_prevented, bit31=valid)
 *     mb[45] = phase95_gyro_rtmd (bits0..11=imu_samples_x10, bits12..19=skew_ms_x10,
 *              bits20..21=rtmd_status_idx(0=READY,1=CTR_LOCK,2=SUSP_SQ), bit22=rtmd_suspended_by_sq,
 *              bit23=gyroflow_ready, bit24=fallback_center_lock, bits25..31=squeeze_x50)
 *     mb[46] = phase95_tone_limiter (bit0=ref_tone_req, bit1=ref_tone_eff, bit2=ref_tone_inhibited,
 *              bit3=color_bars_eff, bit4=limiter_en, bit5=limiter_engaging,
 *              bits6..9=ch_clamped_mask, bits10..17=lim_thresh_x10(30), bits18..25=tone_dbfs(20),
 *              bit31=valid)
 *     mb[47] = 0x4759524f ('GYRO') Phase 95 Anamorphic IBIS / Gyroflow 2000Hz RTMD / 1kHz Tone magic tag
 */
#include "fx6_static_assist.h"

extern int dprintf(int, const char *, ...);
extern void *fx6_map_osd(void);
extern void fx6_gds_install(void *fb);
extern void fx6_scan_osd(void);
extern void *calloc(unsigned long, unsigned long);
extern void *memset(void *, int, unsigned long);
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

/* Cached dynamic symbols resolved once at startup (eliminates ~1,500 dlsym walks/frame) */
typedef struct {
    int ready;
    void *(*sys_getImageData)(void *);
    int (*addArena)(unsigned char, const void *);
    int (*loadFontData)(unsigned int);
    void (*string_ctor)(void *);
    void (*string_dtor)(void *);
    const char *(*ptrBuffer)(const void *);
    int (*getText)(unsigned int, void *);
    void (*setImageLoadCallback)(void *, void *, void *);
    void (*drawTextImpl)(void *);
    int (*processCommands)(unsigned int);
    void (*setRectPos)(void *, unsigned short, const void *);
    void (*renderRect)(void *, const void *, const void *, float, float);
    void (*dict_ctor)(void *);
    void *(*removeFirst)(void *);
    void (*imageOnLoad)(void *);
    void *(*rmGetInstance)(void);
    void *(*rmGetAllocator)(void *);
    void *imageElemOnLoadedCb;
    unsigned short (*imgGetWidth)(const void *);
    unsigned short (*imgGetHeight)(const void *);
    unsigned short (*imgGetLeft)(const void *);
    unsigned short (*imgGetTop)(const void *);
    int (*imgGetPixelFormat)(const void *);
    void (*setToDecodeImmediately)(void *, int);
    void (*setImageCallback)(void *, void *, void *, int);
    int (*getImageSize)(unsigned int, unsigned short *, unsigned short *);
    int (*setFontNameWithNamespace)(unsigned short);
    int (*switchBank)(unsigned short, unsigned char);
} fx6_syms_t;

static fx6_syms_t g_syms;
static uint32_t g_cur_lang;

static uint32_t fx6_font_ns_rid(void) {
    switch (g_cur_lang) {
    case 1u: return 0x0200a01cU; /* FONT_S_CHINESE */
    case 2u: return 0x0200a006U; /* FONT_JAPANESE */
    default: return 0x0200a005U; /* FONT_UNIVERS */
    }
}

/* 32-slot aligned widget ring pools prevent tid=220/async commands from racing zeroed buffers */
#define FX6_WIDGET_POOL_N 32u
static unsigned char s_vs_pool[FX6_WIDGET_POOL_N][0x1400] __attribute__((aligned(16)));
static unsigned char s_vf_pool[FX6_WIDGET_POOL_N][0x1180] __attribute__((aligned(16)));
static unsigned char s_ic_pool[FX6_WIDGET_POOL_N][0x700]  __attribute__((aligned(16)));
static unsigned int s_vs_next, s_vf_next, s_ic_next;
static unsigned char s_dict_buf[0x80] __attribute__((aligned(16)));
static int s_dict_ready;

typedef struct {
    int done;
    int blitted;
    int dst_x;
    int dst_y;
    int dst_w;
    int dst_h;
    uint32_t tint_rgb;
    uint32_t img_rid;
} fx6_icon_ctx_t;

static fx6_icon_ctx_t s_icon_ctx[FX6_WIDGET_POOL_N];
static uint32_t s_bad_icon_rids[64];
static unsigned int s_bad_icon_next;

#define FX6_ICON_CACHE_MAX 512u
#define FX6_ICON_SLAB_BYTES (16u * 1024u * 1024u)
typedef struct {
    uint32_t rid;
    uint16_t sw;
    uint16_t sh;
    uint32_t *pixels;
} fx6_icon_cache_entry_t;

static fx6_icon_cache_entry_t s_icon_cache[FX6_ICON_CACHE_MAX];
static unsigned int s_icon_cache_n;
static uint8_t *g_icon_slab;
static unsigned long g_icon_slab_used;

static int fx6_valid_ptr(const void *p) {
    uintptr_t u = (uintptr_t)p;
    return (u >= 0x10000ULL) && ((u >> 48) == 0ULL) && ((u & 3ULL) == 0ULL);
}

static void fx6_init_syms(void) {
    if (g_syms.ready) return;
    g_syms.sys_getImageData = (void *(*)(void *))
        dlsym((void *)-1, "_ZN5libra9ImageData16sys_getImageDataEv");
    g_syms.addArena = (int (*)(unsigned char, const void *))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager8addArenaEhRKN5libra10ArenaParamE");
    g_syms.loadFontData = (int (*)(unsigned int))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager16sys_loadFontDataEj");
    g_syms.string_ctor = (void (*)(void *))
        dlsym((void *)-1, "_ZN5libra6StringC1Ev");
    g_syms.string_dtor = (void (*)(void *))
        dlsym((void *)-1, "_ZN5libra6StringD1Ev");
    g_syms.ptrBuffer = (const char *(*)(const void *))
        dlsym((void *)-1, "_ZNK6stella6String9ptrBufferEv");
    g_syms.getText = (int (*)(unsigned int, void *))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager7getTextEjRN5libra6StringE");
    g_syms.setImageLoadCallback = (void (*)(void *, void *, void *))
        dlsym((void *)-1, "_ZN2ux6gfxeng10TextSprite20setImageLoadCallbackEPFvPS1_PN5libra9ImageDataEPvES6_");
    g_syms.drawTextImpl = (void (*)(void *))
        dlsym((void *)-1, "_ZN2ux6gfxeng10TextSprite12drawTextImplEv");
    g_syms.processCommands = (int (*)(unsigned int))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager15processCommandsEj");
    g_syms.setRectPos = (void (*)(void *, unsigned short, const void *))
        dlsym((void *)-1, "_ZN2ux6gfxeng6Sprite10setRectPosEtRKNS_4core7Vector2E");
    g_syms.renderRect = (void (*)(void *, const void *, const void *, float, float))
        dlsym((void *)-1, "_ZN2ux6gfxeng6Sprite10renderRectERKNS_4core7Vector2ERKNS1_8RectDataEff");
    g_syms.dict_ctor = (void (*)(void *))
        dlsym((void *)-1, "_ZN5libra10DictionaryC1Ev");
    g_syms.removeFirst = (void *(*)(void *))
        dlsym((void *)-1, "_ZN6stella10LinearList11removeFirstEv");
    g_syms.imageOnLoad = (void (*)(void *))
        dlsym((void *)-1, "_ZN5libra9ImageData6onLoadEv");
    g_syms.rmGetInstance = (void *(*)(void))
        dlsym((void *)-1, "_ZN5libra15ResourceManager11getInstanceEv");
    g_syms.rmGetAllocator = (void *(*)(void *))
        dlsym((void *)-1, "_ZN5libra15ResourceManager12getAllocatorEv");
    g_syms.imageElemOnLoadedCb =
        dlsym((void *)-1, "_ZN2ux6gfxeng16ImageElementBase21onLoadedImageCallbackEPvPN5libra9ImageDataE");
    g_syms.imgGetWidth = (unsigned short (*)(const void *))
        dlsym((void *)-1, "_ZNK5libra9ImageData8getWidthEv");
    g_syms.imgGetHeight = (unsigned short (*)(const void *))
        dlsym((void *)-1, "_ZNK5libra9ImageData9getHeightEv");
    g_syms.imgGetLeft = (unsigned short (*)(const void *))
        dlsym((void *)-1, "_ZNK5libra9ImageData7getLeftEv");
    g_syms.imgGetTop = (unsigned short (*)(const void *))
        dlsym((void *)-1, "_ZNK5libra9ImageData6getTopEv");
    g_syms.imgGetPixelFormat = (int (*)(const void *))
        dlsym((void *)-1, "_ZNK5libra9ImageData14getPixelFormatEv");
    g_syms.setToDecodeImmediately = (void (*)(void *, int))
        dlsym((void *)-1, "_ZN2ux6gfxeng16ImageElementBase22setToDecodeImmediatelyEb");
    g_syms.setImageCallback = (void (*)(void *, void *, void *, int))
        dlsym((void *)-1, "_ZN2ux6gfxeng16ImageElementBase16setImageCallbackEPFvPviRKN5libra9ImageDataEES2_i");
    g_syms.getImageSize = (int (*)(unsigned int, unsigned short *, unsigned short *))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager12getImageSizeEjRtS2_");
    g_syms.setFontNameWithNamespace = (int (*)(unsigned short))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager28sys_setFontNameWithNamespaceEt");
    g_syms.switchBank = (int (*)(unsigned short, unsigned char))
        dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager10switchBankEth");
    __sync_synchronize();
    g_syms.ready = 1;
}

static void fx6_apply_lang(uint32_t lang) {
    if (lang > 2u) lang = 0u;
    if (lang == g_cur_lang) return;
    unsigned char bank = 4u;
    if (lang == 1u) bank = 19u;
    else if (lang == 2u) bank = 12u;
    if (g_syms.switchBank) {
        g_syms.switchBank(1, bank);
        g_syms.switchBank(2, bank);
    }
    g_cur_lang = lang;
    dprintf(2, "FX6_LIVE_LANG lang=%u bank=%u font_ns=0x%08x\n",
            lang, (unsigned)bank, fx6_font_ns_rid());
}

static void fx6_drain_commands(int max_iters) {
    if (!g_syms.processCommands) return;
    for (int k = 0; k < max_iters; k++) {
        if (g_syms.processCommands(0) <= 0) break;
    }
}

/* Complete-object destructor (Itanium C++ ABI vtable slot 0 = D1Ev, does NOT free memory) */
static inline void fx6_destroy_widget_inplace(void *obj) {
    if (!obj) return;
    void **vt = *(void ***)obj;
    if (vt && vt[0]) {
        ((void (*)(void *))vt[0])(obj);
    }
}

/* Guard PLT call from libra::GenerateImageCommand::notify(bool) when an unloaded
 * icon/glyph yields Listener::m_imageData == NULL (prevents str xzr,[0,#8] SIGSEGV). */
void _ZN5libra9ImageData6onLoadEv(void *self) {
    if (!self) return;
    *(uint64_t *)((char *)self + 0x8) = 0;
}

/* Interpose libra::GenerateImageCommand::notify(bool) directly (tail-called via PLT
 * from settle(bool) at liblibra.so + 0x2a2e8). Prevents blr x2 with x2==0 or x1==0
 * when ImageData::detach() or widget teardown races async command settlement. */
void _ZN5libra20GenerateImageCommand6notifyEb(void *self, int ok) {
    (void)ok;
    if (!fx6_valid_ptr(self)) return;
    fx6_init_syms();
    if (!g_syms.removeFirst) return;
    void *list = (char *)self + 0x28;
    for (int guard = 0; guard < 1024; guard++) {
        void *node = g_syms.removeFirst(list);
        if (!node) break;
        if (!fx6_valid_ptr(node)) break;
        void *arg = *(void **)((char *)node + 0x08);
        void *cb  = *(void **)((char *)node + 0x10);
        void *img = *(void **)((char *)node + 0x18);
        if (img && fx6_valid_ptr(img) && g_syms.imageOnLoad) {
            g_syms.imageOnLoad(img);
        }
        if (cb != 0 && img != 0 && (uintptr_t)cb > 0x10000ULL &&
            fx6_valid_ptr(cb) && fx6_valid_ptr(img) &&
            (!arg || fx6_valid_ptr(arg)) &&
            !(g_syms.imageElemOnLoadedCb && cb == g_syms.imageElemOnLoadedCb && !arg)) {
            ((void (*)(void *, void *))cb)(arg, img);
        }
        if (g_syms.rmGetInstance && g_syms.rmGetAllocator) {
            void *rm = g_syms.rmGetInstance();
            if (fx6_valid_ptr(rm)) {
                void *alloc = g_syms.rmGetAllocator(rm);
                if (fx6_valid_ptr(alloc)) {
                    void **avt = *(void ***)alloc;
                    if (fx6_valid_ptr(avt) && avt[2] && fx6_valid_ptr(avt[2])) {
                        ((void (*)(void *, void *))avt[2])(alloc, node);
                    }
                }
            }
        }
    }
}

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

/* ---------------- native text & icon ImageData -> OSD -------------------- */
static int fx6_blit_imagedata_rect_to_osd(void *image, uint32_t *osd,
                                          int dst_x, int dst_y, int dst_w, int dst_h,
                                          uint32_t tint_rgb) {
    if (!image || !osd) return 0;
    fx6_init_syms();
    if (!g_syms.sys_getImageData) return 0;
    uint8_t *raw = (uint8_t *)g_syms.sys_getImageData(image);
    if (!raw || !fx6_valid_ptr(raw)) return 0;
    int raw_w = (int)(*(uint16_t *)(raw + 0x00));
    int raw_h = (int)(*(uint16_t *)(raw + 0x02));
    int pitch_px = (int)(*(uint32_t *)(raw + 0x04));
    int stella_fmt = *(int *)(raw + 0x0c);
    void *bmp = *(void **)(raw + 0x18);
    if (!bmp || !fx6_valid_ptr(bmp) || raw_w <= 0 || raw_h <= 0) return 0;
    const uint8_t *bits = *(const uint8_t **)((uint8_t *)bmp + 0x10);
    if (!bits || !fx6_valid_ptr(bits)) return 0;

    const uint8_t *info = *(const uint8_t **)((uint8_t *)bmp + 0x08);
    int bw = raw_w, bh = raw_h, stride_px = pitch_px, bmp_fmt = 0;
    if (fx6_valid_ptr(info)) {
        int iw = (int)(*(const short *)(info + 0x08));
        int ih = (int)(*(const short *)(info + 0x0a));
        int aw = (int)(*(const short *)(info + 0x18));
        if (iw > 0) bw = iw;
        if (ih > 0) bh = ih;
        if (aw > 0) stride_px = aw;
        bmp_fmt = *(const int *)(info + 0x1c);
    }
    if (stride_px <= 0) stride_px = bw;

    if (stella_fmt == 0 && g_syms.imgGetPixelFormat) {
        stella_fmt = g_syms.imgGetPixelFormat(image);
    }
    /* Map stella_fmt / BMP_PixelFormat:
     *   mode 1: RGBA4444 (stella=7 or bmp_fmt=1, 2 Bpp)
     *   mode 2: RGBA8888 (stella=1 or bmp_fmt=2, 4 Bpp, bytes [R,G,B,A])
     *   mode 3: A8 tint  (stella=8 or bmp_fmt=4, 1 Bpp)
     *   mode 4: ARGB4444 (bmp_fmt=3, 2 Bpp)
     */
    int mode = 1, bpp = 2;
    if (bmp_fmt == 2 || stella_fmt == 1) {
        mode = 2; bpp = 4;
    } else if (bmp_fmt == 4 || stella_fmt == 8) {
        mode = 3; bpp = 1;
    } else if (bmp_fmt == 3) {
        mode = 4; bpp = 2;
    } else {
        mode = 1; bpp = 2;
    }

    int sx0 = g_syms.imgGetLeft ? (int)g_syms.imgGetLeft(image) : 0;
    int sy0 = g_syms.imgGetTop ? (int)g_syms.imgGetTop(image) : 0;
    int sw = g_syms.imgGetWidth ? (int)g_syms.imgGetWidth(image) : raw_w;
    int sh = g_syms.imgGetHeight ? (int)g_syms.imgGetHeight(image) : raw_h;
    if (sw <= 0 || sh <= 0) { sx0 = 0; sy0 = 0; sw = raw_w; sh = raw_h; }
    if (sx0 < 0) sx0 = 0;
    if (sy0 < 0) sy0 = 0;
    if (sx0 >= bw || sy0 >= bh) return 0;
    if (sx0 + sw > bw) sw = bw - sx0;
    if (sy0 + sh > bh) sh = bh - sy0;
    if (sw <= 0 || sh <= 0) return 0;

    int out_w = (dst_w > 0) ? dst_w : sw;
    int out_h = (dst_h > 0) ? dst_h : sh;
    if (out_w > 1024) out_w = 1024;
    if (out_h > 540) out_h = 540;

    int stride_bytes = stride_px * bpp;
    uint32_t tr = (tint_rgb >> 16) & 0xffu;
    uint32_t tg = (tint_rgb >> 8)  & 0xffu;
    uint32_t tb = tint_rgb & 0xffu;
    int copied = 0;

    for (int y = 0; y < out_h; y++) {
        int dy = dst_y + y;
        if (dy < 0 || dy >= 540) continue;
        int sy = sy0 + (y * sh) / out_h;
        if (sy < 0 || sy >= bh) continue;
        const uint8_t *srow = bits + (unsigned long)sy * (unsigned long)stride_bytes;
        uint32_t *drow = osd + (unsigned long)dy * 1024UL;
        for (int x = 0; x < out_w; x++) {
            int dx = dst_x + x;
            if (dx < 0 || dx >= 1024) continue;
            int sx = sx0 + (x * sw) / out_w;
            if (sx < 0 || sx >= bw) continue;
            uint32_t sr = 0, sg = 0, sb = 0, sa = 0;
            if (mode == 2) {
                const uint8_t *px4 = srow + (unsigned long)sx * 4UL;
                sr = px4[0]; sg = px4[1]; sb = px4[2]; sa = px4[3];
            } else if (mode == 3) {
                sa = srow[sx]; sr = tr; sg = tg; sb = tb;
            } else if (mode == 4) {
                uint16_t pv = ((const uint16_t *)srow)[sx];
                sa = ((pv >> 12) & 0xfu) * 17u;
                sr = ((pv >>  8) & 0xfu) * 17u;
                sg = ((pv >>  4) & 0xfu) * 17u;
                sb = (pv & 0xfu) * 17u;
            } else {
                uint16_t pv = ((const uint16_t *)srow)[sx];
                sr = ((pv >> 12) & 0xfu) * 17u;
                sg = ((pv >>  8) & 0xfu) * 17u;
                sb = ((pv >>  4) & 0xfu) * 17u;
                sa = (pv & 0xfu) * 17u;
            }
            if (sa == 0) continue;
            if (sa >= 255u) {
                drow[dx] = 0xFF000000u | (sr << 16) | (sg << 8) | sb;
            } else {
                uint32_t dst = drow[dx];
                uint32_t dr = dst ? ((dst >> 16) & 0xffu) : 14u;
                uint32_t dg = dst ? ((dst >> 8)  & 0xffu) : 16u;
                uint32_t db = dst ? (dst & 0xffu)         : 20u;
                uint32_t or_c = (sr * sa + dr * (255u - sa)) / 255u;
                uint32_t og_c = (sg * sa + dg * (255u - sa)) / 255u;
                uint32_t ob_c = (sb * sa + db * (255u - sa)) / 255u;
                drow[dx] = 0xFF000000u | (or_c << 16) | (og_c << 8) | ob_c;
            }
            copied++;
        }
    }
    return copied;
}

static int fx6_blit_imagedata_to_osd(void *image, uint32_t *osd, int dst_x, int dst_y) {
    return fx6_blit_imagedata_rect_to_osd(image, osd, dst_x, dst_y, 0, 0, 0xFFFFFFu);
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

static const fx6_icon_cache_entry_t *fx6_icon_cache_find(uint32_t rid) {
    for (unsigned int i = 0; i < s_icon_cache_n; i++) {
        if (s_icon_cache[i].rid == rid && s_icon_cache[i].pixels) {
            return &s_icon_cache[i];
        }
    }
    return 0;
}

static void fx6_icon_cache_put(uint32_t rid, void *image) {
    if (!rid || !image || !g_icon_slab || s_icon_cache_n >= FX6_ICON_CACHE_MAX) return;
    if (fx6_icon_cache_find(rid)) return;
    if (!g_syms.sys_getImageData) return;
    uint8_t *raw = (uint8_t *)g_syms.sys_getImageData(image);
    if (!raw || !fx6_valid_ptr(raw)) return;
    int raw_w = (int)(*(uint16_t *)(raw + 0x00));
    int raw_h = (int)(*(uint16_t *)(raw + 0x02));
    int pitch_px = (int)(*(uint32_t *)(raw + 0x04));
    int stella_fmt = *(int *)(raw + 0x0c);
    void *bmp = *(void **)(raw + 0x18);
    if (!bmp || !fx6_valid_ptr(bmp) || raw_w <= 0 || raw_h <= 0) return;
    const uint8_t *bits = *(const uint8_t **)((uint8_t *)bmp + 0x10);
    if (!bits || !fx6_valid_ptr(bits)) return;
    const uint8_t *info = *(const uint8_t **)((uint8_t *)bmp + 0x08);
    int bw = raw_w, bh = raw_h, stride_px = pitch_px, bmp_fmt = 0;
    if (fx6_valid_ptr(info)) {
        int iw = (int)(*(const short *)(info + 0x08));
        int ih = (int)(*(const short *)(info + 0x0a));
        int aw = (int)(*(const short *)(info + 0x18));
        if (iw > 0) bw = iw;
        if (ih > 0) bh = ih;
        if (aw > 0) stride_px = aw;
        bmp_fmt = *(const int *)(info + 0x1c);
    }
    if (stride_px <= 0) stride_px = bw;
    if (stella_fmt == 0 && g_syms.imgGetPixelFormat) stella_fmt = g_syms.imgGetPixelFormat(image);
    int mode = 1, bpp = 2;
    if (bmp_fmt == 2 || stella_fmt == 1) { mode = 2; bpp = 4; }
    else if (bmp_fmt == 4 || stella_fmt == 8) { mode = 3; bpp = 1; }
    else if (bmp_fmt == 3) { mode = 4; bpp = 2; }
    int sx0 = g_syms.imgGetLeft ? (int)g_syms.imgGetLeft(image) : 0;
    int sy0 = g_syms.imgGetTop ? (int)g_syms.imgGetTop(image) : 0;
    int sw = g_syms.imgGetWidth ? (int)g_syms.imgGetWidth(image) : raw_w;
    int sh = g_syms.imgGetHeight ? (int)g_syms.imgGetHeight(image) : raw_h;
    if (sw <= 0 || sh <= 0) { sx0 = 0; sy0 = 0; sw = raw_w; sh = raw_h; }
    if (sx0 < 0) sx0 = 0;
    if (sy0 < 0) sy0 = 0;
    if (sx0 >= bw || sy0 >= bh) return;
    if (sx0 + sw > bw) sw = bw - sx0;
    if (sy0 + sh > bh) sh = bh - sy0;
    if (sw <= 0 || sh <= 0 || sw > 1024 || sh > 540) return;

    unsigned long need = (unsigned long)sw * (unsigned long)sh * 4UL;
    if (g_icon_slab_used + need > FX6_ICON_SLAB_BYTES) return;
    uint32_t *dst = (uint32_t *)(g_icon_slab + g_icon_slab_used);
    int stride_bytes = stride_px * bpp;
    for (int y = 0; y < sh; y++) {
        const uint8_t *srow = bits + (unsigned long)(sy0 + y) * (unsigned long)stride_bytes;
        uint32_t *drow = dst + (unsigned long)y * (unsigned long)sw;
        for (int x = 0; x < sw; x++) {
            int sx = sx0 + x;
            uint32_t sr = 0, sg = 0, sb = 0, sa = 0;
            if (mode == 2) {
                const uint8_t *px4 = srow + (unsigned long)sx * 4UL;
                sr = px4[0]; sg = px4[1]; sb = px4[2]; sa = px4[3];
            } else if (mode == 3) {
                sa = srow[sx]; sr = 0xffu; sg = 0xffu; sb = 0xffu;
            } else if (mode == 4) {
                uint16_t pv = ((const uint16_t *)srow)[sx];
                sa = ((pv >> 12) & 0xfu) * 17u;
                sr = ((pv >>  8) & 0xfu) * 17u;
                sg = ((pv >>  4) & 0xfu) * 17u;
                sb = (pv & 0xfu) * 17u;
            } else {
                uint16_t pv = ((const uint16_t *)srow)[sx];
                sr = ((pv >> 12) & 0xfu) * 17u;
                sg = ((pv >>  8) & 0xfu) * 17u;
                sb = ((pv >>  4) & 0xfu) * 17u;
                sa = (pv & 0xfu) * 17u;
            }
            drow[x] = (sa << 24) | (sr << 16) | (sg << 8) | sb;
        }
    }
    fx6_icon_cache_entry_t *e = &s_icon_cache[s_icon_cache_n++];
    e->rid = rid;
    e->sw = (uint16_t)sw;
    e->sh = (uint16_t)sh;
    e->pixels = dst;
    g_icon_slab_used += (need + 15UL) & ~15UL;
}

static int fx6_blit_cached_icon_to_osd(const fx6_icon_cache_entry_t *e, uint32_t *osd,
                                       int dst_x, int dst_y, int dst_w, int dst_h) {
    if (!e || !e->pixels || !osd || e->sw == 0 || e->sh == 0) return 0;
    int sw = (int)e->sw, sh = (int)e->sh;
    int draw_x = dst_x, draw_y = dst_y;
    int draw_w = dst_w, draw_h = dst_h;
    if (dst_w > 0 && dst_h > 0) {
        if (sw <= dst_w && sh <= dst_h) {
            draw_w = sw;
            draw_h = sh;
        } else {
            if (sw * dst_h >= sh * dst_w) {
                draw_w = dst_w;
                draw_h = (sh * dst_w) / sw;
            } else {
                draw_h = dst_h;
                draw_w = (sw * dst_h) / sh;
            }
            if (draw_w < 1) draw_w = 1;
            if (draw_h < 1) draw_h = 1;
        }
        draw_x = dst_x + (dst_w - draw_w) / 2;
        draw_y = dst_y + (dst_h - draw_h) / 2;
    } else {
        draw_w = sw;
        draw_h = sh;
    }
    if (draw_w > 1024) draw_w = 1024;
    if (draw_h > 540) draw_h = 540;
    int copied = 0;
    for (int y = 0; y < draw_h; y++) {
        int dy = draw_y + y;
        if (dy < 0 || dy >= 540) continue;
        int sy = (y * sh) / draw_h;
        const uint32_t *srow = e->pixels + (unsigned long)sy * (unsigned long)sw;
        uint32_t *drow = osd + (unsigned long)dy * 1024UL;
        for (int x = 0; x < draw_w; x++) {
            int dx = draw_x + x;
            if (dx < 0 || dx >= 1024) continue;
            int sx = (x * sw) / draw_w;
            uint32_t sp = srow[sx];
            uint32_t sa = (sp >> 24) & 0xffu;
            if (sa == 0) continue;
            uint32_t sr = (sp >> 16) & 0xffu;
            uint32_t sg = (sp >> 8) & 0xffu;
            uint32_t sb = sp & 0xffu;
            if (sa >= 255u) {
                drow[dx] = 0xFF000000u | (sr << 16) | (sg << 8) | sb;
            } else {
                uint32_t dst = drow[dx];
                uint32_t dr = dst ? ((dst >> 16) & 0xffu) : 14u;
                uint32_t dg = dst ? ((dst >> 8)  & 0xffu) : 16u;
                uint32_t db = dst ? (dst & 0xffu)         : 20u;
                uint32_t or_c = (sr * sa + dr * (255u - sa)) / 255u;
                uint32_t og_c = (sg * sa + dg * (255u - sa)) / 255u;
                uint32_t ob_c = (sb * sa + db * (255u - sa)) / 255u;
                drow[dx] = 0xFF000000u | (or_c << 16) | (og_c << 8) | ob_c;
            }
            copied++;
        }
    }
    return copied;
}

static void fx6_icon_image_cb(void *ud, int arg, void *image) {
    (void)arg;
    fx6_icon_ctx_t *ctx = (fx6_icon_ctx_t *)ud;
    if (!ctx || !fx6_valid_ptr(ctx)) return;
    if (!image || !fx6_valid_ptr(image)) {
        ctx->done = 1;
        return;
    }
    int sw = g_syms.imgGetWidth ? (int)g_syms.imgGetWidth(image) : 0;
    int sh = g_syms.imgGetHeight ? (int)g_syms.imgGetHeight(image) : 0;
    int draw_x = ctx->dst_x, draw_y = ctx->dst_y;
    int draw_w = ctx->dst_w, draw_h = ctx->dst_h;
    if (sw > 0 && sh > 0 && ctx->dst_w > 0 && ctx->dst_h > 0) {
        if (sw <= ctx->dst_w && sh <= ctx->dst_h) {
            draw_w = sw;
            draw_h = sh;
        } else {
            if (sw * ctx->dst_h >= sh * ctx->dst_w) {
                draw_w = ctx->dst_w;
                draw_h = (sh * ctx->dst_w) / sw;
            } else {
                draw_h = ctx->dst_h;
                draw_w = (sw * ctx->dst_h) / sh;
            }
            if (draw_w < 1) draw_w = 1;
            if (draw_h < 1) draw_h = 1;
        }
        draw_x = ctx->dst_x + (ctx->dst_w - draw_w) / 2;
        draw_y = ctx->dst_y + (ctx->dst_h - draw_h) / 2;
    }
    fx6_icon_cache_put(ctx->img_rid, image);
    ctx->blitted = fx6_blit_imagedata_rect_to_osd(image, g_osd, draw_x, draw_y, draw_w, draw_h, ctx->tint_rgb);
    ctx->done = 1;
}

/* ---------------- resources ---------------------------------------------- */
static int fx6_add_arena(int idx, unsigned min, unsigned max) {
    fx6_init_syms();
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
    if (!g_syms.addArena) return 0;
    return g_syms.addArena((unsigned char)idx, (const void *)param);
}

static void fx6_load_fonts(void) {
    fx6_init_syms();
    if (!g_syms.loadFontData) return;
    int ok = 0, total = 0;
    for (unsigned r = 0x02006000U; r <= 0x0200603fU; r++) { total++; if (g_syms.loadFontData(r)) ok++; }
    for (unsigned r = 0x0200a000U; r <= 0x0200a02fU; r++) { total++; if (g_syms.loadFontData(r)) ok++; }
    for (unsigned r = 0x02008000U; r <= 0x0200800fU; r++) { total++; if (g_syms.loadFontData(r)) ok++; }
    dprintf(2, "FX6_LIVE loadFonts ok=%d/%d\n", ok, total);
}

static int fx6_text_of(uint32_t rid, char *out, unsigned outsz) {
    fx6_init_syms();
    out[0] = 0;
    if (!g_syms.string_ctor || !g_syms.ptrBuffer || !g_syms.getText) return 0;
    unsigned char buf[0x40] __attribute__((aligned(16)));
    memset(buf, 0, sizeof(buf));
    g_syms.string_ctor(buf);
    int rc = g_syms.getText(rid, buf);
    const char *s = g_syms.ptrBuffer(buf);
    unsigned n = 0;
    if (rc && s) {
        while (s[n] && n + 1 < outsz) { out[n] = s[n]; n++; }
        out[n] = 0;
    }
    /* Note: ResourceManager::getText binds an arena-less view into mmapped string_english_2.uxc;
     * calling _ZN5libra6StringD1Ev dereferences null arena+0x8 (SIGSEGV in liblibra.so). */
    return n > 0;
}

static uint32_t fx6_pick(uint32_t a, uint32_t b, const char *want, const char *what) {
    char t[0x60];
    if (fx6_text_of(a, t, sizeof(t)) && want && t[0] && strstr_(t, want)) return a;
    if (fx6_text_of(b, t, sizeof(t)) && want && t[0] && strstr_(t, want)) return b;
    (void)what;
    return a;
}

/* ---------------- native widgets ----------------------------------------- */
#define VS_ROW_BASE    0x220u
#define VS_ROW_STRIDE  0x5cu
#define VS_ROW_TYPE    (-4)
#define VS_ROW_VALUE   0x54u
#define VS_ROW_COUNT   0x610u
#define VS_TYPE_STRING 1u
#define VS_TYPE_VALUE  2u

static void fx6_render_string_text_styled(uint64_t appfw, int x, int y, int w, int h,
                                          const char *text, uint32_t font, uint32_t font2,
                                          uint32_t layout, uint32_t d30, uint32_t d34) {
    if (!text || !text[0]) return;
    if (w < 8 || h < 4) return;
    fx6_init_syms();
    unsigned int slot = s_vs_next++ % FX6_WIDGET_POOL_N;
    void *vs = (void *)s_vs_pool[slot];
    memset(vs, 0, sizeof(s_vs_pool[0]));
    char param[0x40];
    memset(param, 0, sizeof(param));
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc3af98ULL))(vs, param);

    *(int32_t *)((char *)vs + 0x1e8) = x;
    *(int32_t *)((char *)vs + 0x1ec) = y;
    *(int32_t *)((char *)vs + 0x1f0) = w;
    *(int32_t *)((char *)vs + 0x1f4) = h;
    *(uint32_t *)((char *)vs + 0x200) = 0xffffffffU;
    *(uint8_t *)((char *)vs + 0x1fc) = 1;
    *(uint32_t *)((char *)vs + 0x208) = font ? font : 0x0200600fU;
    *(uint32_t *)((char *)vs + 0x20c) = font2 ? font2 : 0x0200600eU;
    *(uint32_t *)((char *)vs + 0x210) = layout ? layout : 0x0200a029U;
    *(uint32_t *)((char *)vs + 0xa14) = 0x0200600bU;
    *(int *)((char *)vs + 0x214) = 0;
    if (d30) *(uint32_t *)((char *)vs + 0x218) = d30;
    *(uint32_t *)((char *)vs + 0x21c) = d34 ? d34 : (uint32_t)VS_TYPE_STRING;
    *(uint32_t *)((char *)vs + 0xa30) = fx6_font_ns_rid();
    *(uint32_t *)((char *)vs + 0xa34) = 0xffffffffU;

    char *row0 = (char *)vs + VS_ROW_BASE;
    *(int *)(row0 + VS_ROW_TYPE) = (int)VS_TYPE_STRING;
    unsigned n = 0;
    while (text[n] && n < 83u) {
        row0[n] = text[n];
        n++;
    }
    row0[n] = 0;
    *(int *)((char *)vs + VS_ROW_COUNT) = 1;

    void *ts = (char *)vs + 0xe40;
    if (g_syms.setImageLoadCallback) g_syms.setImageLoadCallback(ts, (void *)fx6_text_image_cb, vs);
    *(unsigned short *)((char *)ts + 0xa8) |= 0x0008;

    void **vt = *(void ***)vs;
    if (vt && vt[0x158 / 8]) {
        ((void (*)(void *))vt[0x158 / 8])(vs);
        *(unsigned short *)((char *)ts + 0xa8) |= 0x0006;
        if (g_syms.drawTextImpl) g_syms.drawTextImpl(ts);
        fx6_drain_commands(16);
        g_text_n++;
    }
    if (g_syms.setImageLoadCallback) g_syms.setImageLoadCallback(ts, 0, 0);
    fx6_drain_commands(8);
    fx6_destroy_widget_inplace(vs);
}

static void fx6_render_string_text(uint64_t appfw, int x, int y, int w, int h,
                                   const char *text, const char *tag_name) {
    (void)tag_name;
    fx6_render_string_text_styled(appfw, x, y, w, h, text,
                                  0x0200600fU, 0x0200600eU, 0x0200a029U, 0u, 1u);
}

static void fx6_render_string_rid(uint64_t appfw, int x, int y, int w, int h,
                                  uint32_t text_resid, const char *tag_name) {
    if (!text_resid || text_resid == 0xffffffffU) return;
    if (w < 8 || h < 4) return;
    fx6_init_syms();
    unsigned int slot = s_vs_next++ % FX6_WIDGET_POOL_N;
    void *vs = (void *)s_vs_pool[slot];
    memset(vs, 0, sizeof(s_vs_pool[0]));
    char param[0x40];
    memset(param, 0, sizeof(param));
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
    *(uint32_t *)((char *)vs + 0xa30) = fx6_font_ns_rid();

    void *ts = (char *)vs + 0xe40;
    if (g_syms.setImageLoadCallback) g_syms.setImageLoadCallback(ts, (void *)fx6_text_image_cb, vs);
    *(unsigned short *)((char *)ts + 0xa8) |= 0x0008;

    void **vt = *(void ***)vs;
    if (vt && vt[0x158 / 8]) {
        ((void (*)(void *))vt[0x158 / 8])(vs);
        *(unsigned short *)((char *)ts + 0xa8) |= 0x0006;
        if (g_syms.drawTextImpl) g_syms.drawTextImpl(ts);
        fx6_drain_commands(16);
        g_text_n++;
    }
    if (g_syms.setImageLoadCallback) g_syms.setImageLoadCallback(ts, 0, 0);
    fx6_drain_commands(8);
    fx6_destroy_widget_inplace(vs);
    (void)tag_name;
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

    fx6_init_syms();
    unsigned int slot = s_vs_next++ % FX6_WIDGET_POOL_N;
    void *vs = (void *)s_vs_pool[slot];
    memset(vs, 0, sizeof(s_vs_pool[0]));
    char param[0x40];
    memset(param, 0, sizeof(param));
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
    *(uint32_t *)((char *)vs + 0xa30) = fx6_font_ns_rid();

    void *ts = (char *)vs + 0xe40;
    if (g_syms.setImageLoadCallback) g_syms.setImageLoadCallback(ts, (void *)fx6_text_image_cb, vs);
    *(unsigned short *)((char *)ts + 0xa8) |= 0x0008;

    int rendered = 0;
    void **vt = *(void ***)vs;
    if (vt && vt[0x158 / 8]) {
        ((void (*)(void *))vt[0x158 / 8])(vs);
        *(unsigned short *)((char *)ts + 0xa8) |= 0x0006;
        if (g_syms.drawTextImpl) g_syms.drawTextImpl(ts);
        fx6_drain_commands(16);
        g_text_n++;
        rendered = 1;
    }
    if (g_syms.setImageLoadCallback) g_syms.setImageLoadCallback(ts, 0, 0);
    fx6_drain_commands(8);
    fx6_destroy_widget_inplace(vs);
    return rendered;
}

static void fx6_fill_rect(uint64_t appfw, int x, int y, int w, int h, uint32_t color_resid) {
    if (w < 1 || h < 1) return;
    fx6_init_syms();
    unsigned int slot = s_vf_next++ % FX6_WIDGET_POOL_N;
    void *vf = (void *)s_vf_pool[slot];
    memset(vf, 0, sizeof(s_vf_pool[0]));
    char param[0x40];
    memset(param, 0, sizeof(param));
    ((void (*)(void *, void *))(uintptr_t)(appfw + 0xc27698ULL))(vf, param);

    *(int32_t *)((char *)vf + 0x1e8) = x;
    *(int32_t *)((char *)vf + 0x1ec) = y;
    *(int32_t *)((char *)vf + 0x1f0) = w;
    *(int32_t *)((char *)vf + 0x1f4) = h;
    if (color_resid) *(uint32_t *)((char *)vf + 0x200) = color_resid;
    *(uint8_t *)((char *)vf + 0x1fc) = 1;

    void **vt = *(void ***)vf;
    if (vt) {
        if (vt[0x148 / 8]) ((void (*)(void *))vt[0x148 / 8])(vf);
        if (vt[0x158 / 8]) {
            ((void (*)(void *))vt[0x158 / 8])(vf);
            fx6_drain_commands(8);
            char *spr = (char *)vf + 0x210;
            char *rects = *(char **)(spr + 0xd0);
            if (rects) {
                float pos[2] = {(float)x, (float)y};
                if (g_syms.setRectPos) g_syms.setRectPos(spr, 0, pos);
                else { *(float *)(rects + 0x00) = pos[0]; *(float *)(rects + 0x04) = pos[1]; }
                if (g_syms.renderRect) g_syms.renderRect(spr, pos, rects, 0.0f, 0.0f);
            }
            g_fill_n++;
        }
    }
    fx6_drain_commands(8);
    fx6_destroy_widget_inplace(vf);
}

static void fx6_icon_blit(uint64_t appfw, int x, int y, int w, int h, uint32_t img) {
    if (w < 1 || h < 1) return;
    if (!img || img == 0xffffffffU) return;
    fx6_init_syms();
    for (int i = 0; i < 64; i++) {
        if (s_bad_icon_rids[i] == img) return;
    }
    const fx6_icon_cache_entry_t *cached = fx6_icon_cache_find(img);
    if (cached) {
        if (fx6_blit_cached_icon_to_osd(cached, g_osd, x, y, w, h) > 0) g_icon_n++;
        return;
    }
    if (g_syms.getImageSize) {
        unsigned short iw = 0, ih = 0;
        if (!g_syms.getImageSize(img, &iw, &ih) || iw == 0 || ih == 0) {
            s_bad_icon_rids[s_bad_icon_next++ % 64u] = img;
            return;
        }
    }

    unsigned int slot = s_ic_next++ % FX6_WIDGET_POOL_N;
    void *ic = (void *)s_ic_pool[slot];
    fx6_icon_ctx_t *ctx = &s_icon_ctx[slot];
    memset(ic, 0, sizeof(s_ic_pool[0]));
    ctx->done = 0;
    ctx->blitted = 0;
    ctx->dst_x = x;
    ctx->dst_y = y;
    ctx->dst_w = w;
    ctx->dst_h = h;
    ctx->tint_rgb = 0xFFFFFFu;
    ctx->img_rid = img;

    char param[0x40];
    memset(param, 0, sizeof(param));
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
    *(uint16_t *)((char *)ic + 0x204) = (uint16_t)w;
    *(uint16_t *)((char *)ic + 0x206) = (uint16_t)h;

    void *spr = (char *)ic + 0x550;
    void **vt = *(void ***)ic;
    if (vt) {
        if (vt[0x148 / 8]) ((void (*)(void *))vt[0x148 / 8])(ic);
        if (g_syms.setToDecodeImmediately) g_syms.setToDecodeImmediately(spr, 1);
        if (g_syms.setImageCallback) g_syms.setImageCallback(spr, (void *)fx6_icon_image_cb, ctx, 0);
        if (vt[0x158 / 8]) ((void (*)(void *))vt[0x158 / 8])(ic);
        for (int t = 0; t < 80 && !ctx->done; t++) {
            fx6_drain_commands(16);
            if (ctx->done) break;
            usleep(500);
        }
        if (ctx->blitted > 0) g_icon_n++;
    }
    if (g_syms.setImageCallback) g_syms.setImageCallback(spr, 0, 0, 0);
    fx6_drain_commands(8);
    fx6_destroy_widget_inplace(ic);
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
    uint32_t glyph_idx;
    int n_vals;
} fx6_cell_spec_t;

static uint32_t g_live_lut_meta = 0u;
static char     g_live_lut_name[28];
static uint32_t g_live_audio_packed = 0x30303030u; /* -12 dB default on ch1..ch4 */
static uint32_t g_live_p40_flags = 0x303u;       /* attached=1, +48V=1, rtmd=0, bk4=1, valid=1 */
static uint32_t g_live_p64_flags = 0x8003000cu;  /* valid=1, p12=1, p4_nd_absent=1, base800, ei_step=6, angle, stby, tally=on */
static uint32_t g_live_p64_shutter_sq = (24u << 20) | 1800u; /* sq_fps=24, angle=180.0 deg */
static uint32_t g_live_p64_tc = 0u;
static uint32_t g_live_p73_wb_look = 0xc0c6af02u; /* valid=1, soft_map=1, S-Cinetone, SL=off, tint=0(99), 5600K, preset_5600k */
static uint32_t g_live_p73_media_clip = 0xa0020020u; /* proxy_eff=1, 16M, simul, clip=1, pos=C, reel=1, cam=A */
static uint32_t g_live_p73_flags2 = 0u;
static uint32_t g_live_p81_touch_af = 0x4e50e780u;    /* af=off, x=480, y=270, pdaf_idx=313 */
static uint32_t g_live_p81_pdaf_mag_fc = 0x64648250u; /* col=16, row=9, mag=1x, fc=off, clean_hdmi=1, eff_ciz=100, req_ciz=100 */
static uint32_t g_live_p81_ciz_flags = 0x80000004u;   /* valid=1, rocker_speed=4 */
static uint32_t g_live_p88_shotmark = 0u;             /* total=0, m1=0, m2=0, last_type=0, last_frame=0 */
static uint32_t g_live_p88_iris_audio = 0xa9040118u;  /* valid=1, target_ire=41, pad=0, push=0, ae=0EV, multi, F2.8 */
static uint32_t g_live_p88_user_bits = 0xa0010001u;   /* SMPTE 12M User-Bits A0:01:00:01 */
static uint32_t g_live_p95_anamorphic_ibis = 0x8f032048u; /* valid=1, touch_x=480, yaw=100%, eff=Std, req=Std */
static uint32_t g_live_p95_gyro_rtmd = 0x64857342u;       /* sq=1.0(50), ready=1, skew=8.7ms(87), imu=83.4(834) */
static uint32_t g_live_p95_tone_limiter = 0x80507800u;    /* valid=1, tone=-20dBFS, lim=-3.0dBFS */
static char     g_lut_disp_buf[40];
static char     g_lut_hud_buf[24];

static void fx6_osd_fill_rect(int x, int y, int w, int h, uint32_t argb) {
    if (!g_osd || w <= 0 || h <= 0) return;
    int x0 = (x < 0) ? 0 : x;
    int y0 = (y < 0) ? 0 : y;
    int x1 = x + w;
    int y1 = y + h;
    if (x1 > FX6_W) x1 = FX6_W;
    if (y1 > FX6_H) y1 = FX6_H;
    for (int py = y0; py < y1; py++) {
        uint32_t *row = g_osd + (unsigned long)py * (unsigned long)FX6_W;
        for (int px = x0; px < x1; px++) {
            row[px] = argb;
        }
    }
}

static void fx6_osd_border_rect(int x, int y, int w, int h, uint32_t argb) {
    if (w < 2 || h < 2) return;
    fx6_osd_fill_rect(x, y, w, 1, argb);
    fx6_osd_fill_rect(x, y + h - 1, w, 1, argb);
    fx6_osd_fill_rect(x, y, 1, h, argb);
    fx6_osd_fill_rect(x + w - 1, y, 1, h, argb);
}

static void fx6_unpack_lut_name(const volatile uint32_t *mb, char *out, unsigned max_len) {
    if (!out || max_len == 0u) return;
    out[0] = 0;
    if (!mb) return;
    unsigned pos = 0u;
    for (unsigned w = 0u; w < 6u && pos + 1u < max_len; w++) {
        uint32_t word = mb[20u + w];
        for (unsigned b = 0u; b < 4u && pos + 1u < max_len; b++) {
            unsigned char ch = (unsigned char)((word >> (b * 8u)) & 0xffu);
            if (ch == 0u) {
                out[pos] = 0;
                return;
            }
            out[pos++] = (ch >= 0x20u && ch <= 0x7eu) ? (char)ch : '?';
        }
    }
    out[pos] = 0;
}

static const fx6_cell_spec_t g_cell_specs[6] = {
    /* 0: FPS */
    { 0x02005082u, 0u, 7 },
    /* 1: EI / Base ISO */
    { 0x02004c32u, 2u, 6 },
    /* 2: Shutter Angle / Speed */
    { 0x020050e8u, 1u, 7 },
    /* 3: ND Filter (P4 Hardware-Locked on non-ND FX3 sensor body) */
    { 0x02004288u, 3u, 1 },
    /* 4: Base Look / 3D LUT */
    { 0x020023f8u, 5u, 8 },
    /* 5: White Balance */
    { 0x02005689u, 4u, 6 },
};

static const char * const g_cell_val_strs[6][8] = {
    /* 0: FPS */
    { "23.98p", "24.00p", "25.00p", "29.97p", "50.00p", "59.94p", "119.88p (S&Q)", 0 },
    /* 1: EI / Base ISO (Dual Base ISO 800 / 12800) */
    { "800 EI (800 Base)", "400 EI (800 Base)", "1600 EI (800 Base)",
      "12800 EI (12800 Base)", "6400 EI (12800 Base)", "25600 EI (12800 Base)", 0, 0 },
    /* 2: Shutter Angle / Speed (BK4 0x02cf1702 / 0x02cf1704) */
    { "180.0\xc2\xb0", "90.0\xc2\xb0", "45.0\xc2\xb0", "360.0\xc2\xb0", "1/48", "1/50", "1/100", 0 },
    /* 3: ND Filter (P4 Hardware Contract) */
    { "Clear [FX3 P4 Locked]", 0, 0, 0, 0, 0, 0, 0 },
    /* 4: Base Look / 3D LUT (P1 /dev/nflasha30 + P11 0x0165/0x0166) */
    { "S-Cinetone", "S-Log3.Cine / S-Gamut3.Cine", "s709",
      "R709 (800%)", "User1 (33\xc2\xb3 .cube)", "User2 (33\xc2\xb3 .cube)",
      "User3 (33\xc2\xb3 .cube)", "User4 (33\xc2\xb3 .cube)" },
    /* 5: White Balance */
    { "5600K", "4300K", "3200K", "ATW", "Mem A", "Mem B", 0, 0 },
};

static const char * const g_cell_hud_strs[6][8] = {
    /* 0: FPS (narrow HUD) */
    { "23.98p", "24.00p", "25.00p", "29.97p", "50.00p", "59.94p", "119.88p", 0 },
    /* 1: EI (narrow HUD) */
    { "800 EI", "400 EI", "1600 EI", "12800EI", "6400 EI", "25600EI", 0, 0 },
    /* 2: Shutter */
    { "180.0\xc2\xb0", "90.0\xc2\xb0", "45.0\xc2\xb0", "360.0\xc2\xb0", "1/48", "1/50", "1/100", 0 },
    /* 3: ND Filter */
    { "Clear[P4]", 0, 0, 0, 0, 0, 0, 0 },
    /* 4: LUT (medium HUD) */
    { "S-Cinetone", "S-Log3.Cine", "s709", "R709 800%",
      "User1 .cube", "User2 .cube", "User3 .cube", "User4 .cube" },
    /* 5: WB */
    { "5600K", "4300K", "3200K", "ATW", "Mem A", "Mem B", 0, 0 },
};

static const char *fx6_cell_val_str(int cell_idx, const uint32_t *cell_vals) {
    if (cell_idx < 0 || cell_idx >= 6) return "S-Cinetone";
    if (cell_idx == 3) return g_cell_val_strs[3][0];
    int n = g_cell_specs[cell_idx].n_vals;
    uint32_t idx = cell_vals ? (cell_vals[cell_idx] % (uint32_t)n) : 0u;
    if (cell_idx == 4 && idx >= 4u && g_live_lut_name[0]) {
        unsigned slot_num = idx - 3u;
        g_lut_disp_buf[0] = 'U';
        g_lut_disp_buf[1] = 's';
        g_lut_disp_buf[2] = 'r';
        g_lut_disp_buf[3] = (char)('0' + slot_num);
        g_lut_disp_buf[4] = ':';
        g_lut_disp_buf[5] = ' ';
        unsigned p = 6u;
        for (unsigned i = 0u; g_live_lut_name[i] && p + 1u < sizeof(g_lut_disp_buf); i++) {
            g_lut_disp_buf[p++] = g_live_lut_name[i];
        }
        g_lut_disp_buf[p] = 0;
        return g_lut_disp_buf;
    }
    const char *s = g_cell_val_strs[cell_idx][idx];
    return s ? s : g_cell_val_strs[cell_idx][0];
}

static const char *fx6_cell_hud_str(int cell_idx, const uint32_t *cell_vals) {
    if (cell_idx < 0 || cell_idx >= 6) return "S-Cinetone";
    if (cell_idx == 3) return g_cell_hud_strs[3][0];
    int n = g_cell_specs[cell_idx].n_vals;
    uint32_t idx = cell_vals ? (cell_vals[cell_idx] % (uint32_t)n) : 0u;
    if (cell_idx == 4 && idx >= 4u && g_live_lut_name[0]) {
        unsigned slot_num = idx - 3u;
        g_lut_hud_buf[0] = 'U';
        g_lut_hud_buf[1] = (char)('0' + slot_num);
        g_lut_hud_buf[2] = ':';
        unsigned p = 3u;
        for (unsigned i = 0u; g_live_lut_name[i] && p + 1u < 16u; i++) {
            g_lut_hud_buf[p++] = g_live_lut_name[i];
        }
        g_lut_hud_buf[p] = 0;
        return g_lut_hud_buf;
    }
    const char *s = g_cell_hud_strs[cell_idx][idx];
    return s ? s : g_cell_hud_strs[cell_idx][0];
}

/* Page 0: Big-6 Home (TABLE 0x2e9e210, 98 rows) */
static void render_page_big6_home(uint64_t appfw, uint32_t sel_box, const uint32_t *cell_vals) {
    fx6_init_syms();
    uint8_t *base = (uint8_t *)(uintptr_t)(appfw + 0x2e9e210ULL);
    int (*proccmd)(unsigned int) = g_syms.processCommands;

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
                /* Center Base Look / 3D LUT string reflects cell_vals[4] */
                if (resid == 0x02002464u && cell_vals) {
                    fx6_render_string_text(appfw, x, y, w, h, fx6_cell_val_str(4, cell_vals), "center-look");
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

    uint32_t active_cell = sel_box % 6u;
    for (int c = 0; c < n_cells; c++) {
        uint8_t *p = cell_rows[c];
        uint16_t x = *(uint16_t *)(p + 0x3c), y = *(uint16_t *)(p + 0x3e);
        uint16_t w = *(uint16_t *)(p + 0x40), h = *(uint16_t *)(p + 0x42);
        uint32_t glyph = *(uint32_t *)(uintptr_t)(appfw + 0x23be8d8ULL + (uint64_t)g_cell_specs[c].glyph_idx * 8ULL);
        fx6_fill_rect(appfw, x, y, w, h, 0x0200c008u);
        if (proccmd) proccmd(0);
        fx6_border(appfw, x, y, w, h, ((uint32_t)c == active_cell) ? 0x0200c011u : 0x0200c00eu);
        if (proccmd) proccmd(0);
        fx6_icon_blit(appfw, x + 6, y + 6, 28, 28, glyph);
        if (proccmd) proccmd(0);
        int th = (h * 38) / 100;
        if (th < 18) th = 18;
        fx6_render_string_rid(appfw, x + 36, y + 6, w - 42, th, g_cell_specs[c].title_rid, "cell-title");
        fx6_render_string_text(appfw, x + 8, y + 6 + th, w - 16, h - th - 10,
                               fx6_cell_val_str(c, cell_vals), "cell-value");
        if (c == 4 && ((g_live_lut_meta & 0x01000000u) || (cell_vals && (cell_vals[4] % 8u) >= 4u))) {
            uint32_t sw_rgb = (g_live_lut_meta & 0x01000000u) ? (g_live_lut_meta & 0x00ffffffu) : 0x808080u;
            fx6_osd_fill_rect((int)x + (int)w - 28, (int)y + 8, 20, 20, 0xFF000000u | sw_rgb);
            fx6_osd_border_rect((int)x + (int)w - 28, (int)y + 8, 20, 20, 0xFFE5E7EBu);
        }
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
    fx6_render_string_text(appfw, 534, 193, 290, 32, fx6_cell_val_str(4, cell_vals), "setting-value");
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
        fx6_render_string_text(appfw, x + 8, y + 40, w - 16, h - 46, fx6_cell_val_str(c, cell_vals), "cell-value");
    }
    {
        uint8_t *t = base + 4 * FX6_DESC_STRIDE; /* No7_CENTER_TITLE */
        uint8_t *v = base + 3 * FX6_DESC_STRIDE; /* No8_CENTER_VALUE */
        uint16_t tx = *(uint16_t *)(t + 0x3c), ty = *(uint16_t *)(t + 0x3e);
        uint16_t tw = *(uint16_t *)(t + 0x40), th = *(uint16_t *)(t + 0x42);
        uint16_t vx = *(uint16_t *)(v + 0x3c), vy = *(uint16_t *)(v + 0x3e);
        uint16_t vw = *(uint16_t *)(v + 0x40), vh = *(uint16_t *)(v + 0x42);
        fx6_render_string_rid(appfw, tx, ty, tw, th, g_cell_specs[active_cell].title_rid, "centre-title");
        fx6_render_string_text(appfw, vx, vy, vw, vh, fx6_cell_val_str((int)active_cell, cell_vals), "centre-value");
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
static uint32_t g_live_cells[6] = { 0u, 0u, 0u, 0u, 0u, 0u };
static uint32_t g_live_ibis_xlr = 0u;

static const char * const g_ibis_hud_strs[3] = { "IBIS:Lock", "IBIS:Off", "IBIS:Std" };
static const char * const g_xlr_hud_strs[3]  = { "XLR:+48V",  "XLR:Line", "IntMic" };
static const char * const g_lut_short_strs[8] = { "S-Cine", "SLog3", "s709", "R709", "Usr1", "Usr2", "Usr3", "Usr4" };

static const char *fx6_hud_live_str(const char *name) {
    if (!name) return 0;
    uint32_t ibis_idx = g_live_ibis_xlr & 0x0fu;
    uint32_t xlr_idx  = (g_live_ibis_xlr >> 4) & 0x0fu;
    if (ibis_idx >= 3u) ibis_idx = 0u;
    if (xlr_idx >= 3u) xlr_idx = 0u;
    if ((g_live_p40_flags & 0x200u) && !(g_live_p40_flags & 1u)) {
        xlr_idx = 2u; /* P11 0x91db059b Internal Stereo Mic fallback */
    }

    /* FPS */
    if (!strcmp_(name, "No2048_sandq_frame_rate") ||
        !strcmp_(name, "No21_sandq_frame_rate") ||
        !strcmp_(name, "No1022_sandq_frame_rate_value") ||
        !strcmp_(name, "No1093_sandq_frame_rate_value") ||
        !strcmp_(name, "No7_frame_rate") ||
        !strcmp_(name, "No34_video_fps") ||
        !strcmp_(name, "No422_SQ_FRAME_RATE")) {
        return fx6_cell_hud_str(0, g_live_cells);
    }
    /* EI / Base ISO */
    if (!strcmp_(name, "No30_gain_value") ||
        !strcmp_(name, "No2061_gain_value") ||
        !strcmp_(name, "No1023_gain_value")) {
        return fx6_cell_hud_str(1, g_live_cells);
    }
    if (!strcmp_(name, "No13_base_iso") ||
        !strcmp_(name, "No1010_base_iso") ||
        !strcmp_(name, "No2004_base_iso")) {
        return ((g_live_cells[1] % 6u) >= 3u) ? "12800B" : "800B";
    }
    /* Shutter */
    if (!strcmp_(name, "No18_shutter_value") ||
        !strcmp_(name, "No1015_shutter_value") ||
        !strcmp_(name, "No2059_shutter_value")) {
        return fx6_cell_hud_str(2, g_live_cells);
    }
    /* P4 ND-Clear Lock (suppress redundant adjacent ND label so Clear[P4] never overlaps) */
    if (!strcmp_(name, "No58_nd_filter_mode_nd_filter_clear") ||
        !strcmp_(name, "No1050_nd_filter_mode_nd_filter_clear") ||
        !strcmp_(name, "No2054_nd_filter_mode_nd_filter_clear")) {
        return "";
    }
    if (!strcmp_(name, "No60_nd_filter_value_nd_transmittance") ||
        !strcmp_(name, "No1052_nd_filter_value_nd_transmittance") ||
        !strcmp_(name, "No2055_nd_filter_value_nd_transmittance")) {
        return "Clear[P4]";
    }
    /* Base Look / 3D LUT */
    if (!strcmp_(name, "No1066_base_look") ||
        !strcmp_(name, "No50_monitor_lut")) {
        return fx6_cell_val_str(4, g_live_cells);
    }
    if (!strcmp_(name, "No2090_gamma_display_assist") ||
        !strcmp_(name, "No9_baselook") ||
        !strcmp_(name, "No2009_look_name")) {
        return fx6_cell_hud_str(4, g_live_cells);
    }
    if (!strcmp_(name, "No2031_output_lut2_type") ||
        !strcmp_(name, "No2029_output_lut1_type")) {
        return g_lut_short_strs[g_live_cells[4] % 8u];
    }
    /* White Balance */
    if (!strcmp_(name, "No55_white_balance_value") ||
        !strcmp_(name, "No1047_white_balance_value") ||
        !strcmp_(name, "No2063_white_balance_value")) {
        return fx6_cell_hud_str(5, g_live_cells);
    }
    /* P11 5-axis IBIS Center-Lock & XLR-H1 Audio Status */
    if (!strcmp_(name, "No2040_steady_shot_focal_length")) {
        return g_ibis_hud_strs[ibis_idx];
    }
    if (!strcmp_(name, "No2041_steady_shot_focal_length_unit")) {
        return g_xlr_hud_strs[xlr_idx];
    }
    return 0;
}

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
    fx6_init_syms();
    if (!*(void **)((char *)vs + 0x1030)) {
        if (!s_dict_ready && g_syms.dict_ctor) {
            memset(s_dict_buf, 0, sizeof(s_dict_buf));
            g_syms.dict_ctor(s_dict_buf);
            s_dict_ready = 1;
        }
        if (s_dict_ready) {
            *(void **)((char *)vs + 0x1030) = (void *)s_dict_buf;
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

    const char *live_s = fx6_hud_live_str(name);
    if (live_s) {
        if (live_s[0]) {
            fx6_render_string_text_styled(appfw, x, y, w, h, live_s,
                                          font, font2, layout, d30, d34);
        }
        (void)tag;
        return;
    }

    const hud_bind_t *b = fx6_hud_for(name);
    if (!b && (!d18 || d18 == 0xffffffffU)) return;
    if (!b) {
        char probe[0x60];
        if (!fx6_text_of(d18, probe, sizeof(probe))) return;
    }

    fx6_init_syms();
    unsigned int slot = s_vs_next++ % FX6_WIDGET_POOL_N;
    void *vs = (void *)s_vs_pool[slot];
    memset(vs, 0, sizeof(s_vs_pool[0]));
    char param[0x40];
    memset(param, 0, sizeof(param));
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
    *(uint32_t *)((char *)vs + 0xa30) = fx6_font_ns_rid();

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
    if (g_syms.setImageLoadCallback) g_syms.setImageLoadCallback(ts, (void *)fx6_text_image_cb, vs);
    *(unsigned short *)((char *)ts + 0xa8) |= 0x0008;

    void **vt = *(void ***)vs;
    if (vt && vt[0x158 / 8]) {
        ((void (*)(void *))vt[0x158 / 8])(vs);
        *(unsigned short *)((char *)ts + 0xa8) |= 0x0006;
        if (g_syms.drawTextImpl) g_syms.drawTextImpl(ts);
        fx6_drain_commands(16);
        g_text_n++;
    }
    if (g_syms.setImageLoadCallback) g_syms.setImageLoadCallback(ts, 0, 0);
    fx6_drain_commands(8);
    /* Detach shared static Dictionary before running ~view_string() so it is never operator-deleted */
    *(void **)((char *)vs + 0x1030) = 0;
    fx6_destroy_widget_inplace(vs);
    (void)tag;
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
            uint32_t attached = (g_live_p40_flags & 0x200u) ? (g_live_p40_flags & 1u) : 1u;
            for (int ch = 0; ch < 4; ch++) {
                int bx = x + 8 + ch * 16;
                uint32_t raw_v = (g_live_audio_packed >> (ch * 8)) & 0xffu;
                if (raw_v > 72u) raw_v = 72u;
                if (!attached && ch >= 2) {
                    int bh = 4;
                    fx6_osd_fill_rect(bx, y + h - bh - 4, 10, bh, 0xFF374151u);
                } else {
                    int max_bh = (h > 10) ? (h - 10) : 10;
                    int bh = 4 + (max_bh * (int)raw_v) / 72;
                    if (bh > h - 6) bh = h - 6;
                    uint32_t bar_col = (raw_v >= 60u) ? 0xFFEF4444u : ((raw_v >= 54u) ? 0xFFF59E0Bu : 0xFF10B981u);
                    fx6_osd_fill_rect(bx, y + h - bh - 4, 10, bh, bar_col);
                }
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
        } else if ((tag == 0x42d5a50u && !(w >= 140 && h >= 32)) || tag == 0x42d5800u) {
            uint32_t c = *(uint32_t *)(p + 0x18);
            if (c && c != 0xffffffffU)
                fx6_icon_blit(appfw, x, y, w, h, c);
        }
    }
}

static unsigned fx6_append_cstr(char *dst, unsigned pos, unsigned cap, const char *s) {
    if (!dst || !s) return pos;
    for (unsigned i = 0u; s[i] && pos + 1u < cap; i++) {
        dst[pos++] = s[i];
    }
    dst[pos] = 0;
    return pos;
}

static unsigned fx6_append_db(char *dst, unsigned pos, unsigned cap, int db) {
    if (pos + 4u >= cap) return pos;
    if (db < 0) {
        dst[pos++] = '-';
        db = -db;
    } else {
        dst[pos++] = '+';
    }
    if (db >= 10) dst[pos++] = (char)('0' + (db / 10));
    dst[pos++] = (char)('0' + (db % 10));
    dst[pos] = 0;
    return pos;
}

static void fx6_render_phase40_hud_strip(uint64_t appfw, uint32_t page, const uint32_t *cell_vals) {
    uint32_t p = page % 25u;
    int bx = 0, by = 0, bw = 768, bh = 34;
    if (p <= 3u) {
        bx = 236; by = 10;
    } else if (p == 6u || p == 16u || p == 17u) {
        bx = 152; by = 382;
    } else {
        return;
    }

    uint32_t attached  = (g_live_p40_flags & 0x200u) ? (g_live_p40_flags & 1u) : 1u;
    uint32_t phantom   = (g_live_p40_flags & 0x200u) ? ((g_live_p40_flags >> 1) & 1u) : 1u;
    uint32_t rtmd_mode = (g_live_p40_flags & 0x200u) ? ((g_live_p40_flags >> 4) & 3u) : (g_live_ibis_xlr & 0x0fu);
    if (rtmd_mode > 2u) rtmd_mode = 0u;

    fx6_osd_fill_rect(bx, by, bw, bh, 0xFF101622u);
    fx6_osd_border_rect(bx, by, bw, bh, attached ? 0xFF22D3EEu : 0xFFF59E0Bu);

    uint32_t sw_rgb = (g_live_lut_meta & 0x01000000u) ? (g_live_lut_meta & 0x00ffffffu) : 0x808080u;
    fx6_osd_fill_rect(bx + 6, by + 6, 22, 22, 0xFF000000u | sw_rgb);
    fx6_osd_border_rect(bx + 6, by + 6, 22, 22, 0xFFE5E7EBu);

    char lut_lbl[36];
    const char *lut_s = fx6_cell_hud_str(4, cell_vals);
    fx6_append_cstr(lut_lbl, 0u, sizeof(lut_lbl), lut_s);
    fx6_render_string_text_styled(appfw, bx + 34, by + 5, 198, 24, lut_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);

    /* 4-Ch VU Bars right next to LUT label */
    int vx0 = bx + 238;
    for (int ch = 0; ch < 4; ch++) {
        int vx = vx0 + ch * 11;
        fx6_osd_fill_rect(vx, by + 6, 8, 22, 0xFF1F2937u);
        uint32_t raw_v = (g_live_audio_packed >> (ch * 8)) & 0xffu;
        if (raw_v > 72u) raw_v = 72u;
        if (!attached && ch >= 2) {
            fx6_osd_fill_rect(vx, by + 25, 8, 3, 0xFF4B5563u);
        } else {
            int vh = 3 + (19 * (int)raw_v) / 72;
            uint32_t col = (raw_v >= 60u) ? 0xFFEF4444u : ((raw_v >= 54u) ? 0xFFF59E0Bu : 0xFF10B981u);
            fx6_osd_fill_rect(vx, by + 28 - vh, 8, vh, col);
        }
    }

    int ch1_db = (int)(g_live_audio_packed & 0xffu) - 60;
    int ch2_db = (int)((g_live_audio_packed >> 8) & 0xffu) - 60;
    if (ch1_db > 12) ch1_db = 12;
    if (ch2_db > 12) ch2_db = 12;

    char info_lbl[64];
    unsigned pos = 0u;
    if (!attached) {
        pos = fx6_append_cstr(info_lbl, pos, sizeof(info_lbl), "INT-ST ");
    } else if (phantom) {
        pos = fx6_append_cstr(info_lbl, pos, sizeof(info_lbl), "XLR+48V ");
    } else {
        pos = fx6_append_cstr(info_lbl, pos, sizeof(info_lbl), "XLR-LN ");
    }
    pos = fx6_append_db(info_lbl, pos, sizeof(info_lbl), ch1_db);
    pos = fx6_append_cstr(info_lbl, pos, sizeof(info_lbl), "/");
    pos = fx6_append_db(info_lbl, pos, sizeof(info_lbl), ch2_db);
    if (rtmd_mode == 0u) pos = fx6_append_cstr(info_lbl, pos, sizeof(info_lbl), " E304:5AX");
    else if (rtmd_mode == 1u) pos = fx6_append_cstr(info_lbl, pos, sizeof(info_lbl), " E304:LOCK");
    else pos = fx6_append_cstr(info_lbl, pos, sizeof(info_lbl), " E304:STD");
    pos = fx6_append_cstr(info_lbl, pos, sizeof(info_lbl), " BK4:LOCK");
    (void)pos;

    fx6_render_string_text_styled(appfw, bx + 290, by + 5, 470, 24, info_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
}

static void fx6_osd_blend_px(int x, int y, uint32_t rgb, uint32_t alpha_256) {
    if (!g_osd || x < 0 || x >= FX6_W || y < 0 || y >= FX6_H) return;
    unsigned long idx = (unsigned long)y * (unsigned long)FX6_W + (unsigned long)x;
    uint32_t dst = g_osd[idx];
    uint32_t dr = dst ? ((dst >> 16) & 0xffu) : 14u;
    uint32_t dg = dst ? ((dst >> 8) & 0xffu) : 16u;
    uint32_t db = dst ? (dst & 0xffu) : 20u;
    uint32_t sr = (rgb >> 16) & 0xffu;
    uint32_t sg = (rgb >> 8) & 0xffu;
    uint32_t sb = rgb & 0xffu;
    uint32_t inv = 256u - alpha_256;
    uint32_t rr = (dr * inv + sr * alpha_256) >> 8;
    uint32_t rg = (dg * inv + sg * alpha_256) >> 8;
    uint32_t rb = (db * inv + sb * alpha_256) >> 8;
    g_osd[idx] = 0xFF000000u | (rr << 16) | (rg << 8) | rb;
}

static void fx6_osd_blend_rect(int x, int y, int w, int h, uint32_t rgb, uint32_t alpha_256) {
    if (!g_osd || w <= 0 || h <= 0) return;
    int x0 = (x < 0) ? 0 : x;
    int y0 = (y < 0) ? 0 : y;
    int x1 = x + w;
    int y1 = y + h;
    if (x1 > FX6_W) x1 = FX6_W;
    if (y1 > FX6_H) y1 = FX6_H;
    for (int py = y0; py < y1; py++) {
        for (int px = x0; px < x1; px++) {
            fx6_osd_blend_px(px, py, rgb, alpha_256);
        }
    }
}

static void fx6_draw_corner_ticks(int x0, int y0, int x1, int y1, int tick_len, int thick, uint32_t rgb, uint32_t alpha_256) {
    fx6_osd_blend_rect(x0, y0, tick_len, thick, rgb, alpha_256);
    fx6_osd_blend_rect(x0, y0, thick, tick_len, rgb, alpha_256);
    fx6_osd_blend_rect(x1 - tick_len + 1, y0, tick_len, thick, rgb, alpha_256);
    fx6_osd_blend_rect(x1 - thick + 1, y0, thick, tick_len, rgb, alpha_256);
    fx6_osd_blend_rect(x0, y1 - thick + 1, tick_len, thick, rgb, alpha_256);
    fx6_osd_blend_rect(x0, y1 - tick_len + 1, thick, tick_len, rgb, alpha_256);
    fx6_osd_blend_rect(x1 - tick_len + 1, y1 - thick + 1, tick_len, thick, rgb, alpha_256);
    fx6_osd_blend_rect(x1 - thick + 1, y1 - tick_len + 1, thick, tick_len, rgb, alpha_256);
}

static void fx6_render_phase56_assist_overlays(uint64_t appfw, uint32_t page) {
    (void)page;
    if (!g_osd) return;
    uint32_t aspect_idx    = (g_live_p40_flags >> 12) & 0x07u;
    uint32_t zebra_idx     = (g_live_p40_flags >> 16) & 0x03u;
    uint32_t peaking_idx   = (g_live_p40_flags >> 18) & 0x03u;
    uint32_t desqueeze_idx = (g_live_p40_flags >> 20) & 0x03u;
    if (aspect_idx == 0u && zebra_idx == 0u && peaking_idx == 0u && desqueeze_idx == 0u) {
        return;
    }

    /* Flush all queued appFw/TextRM commands before pixel-level Peaking & Zebra passes */
    if (g_syms.processCommands) g_syms.processCommands(0);

    /* 1. Focus Peaking pass (real luma gradient edge detection on g_osd) */
    if (peaking_idx > 0u) {
        uint32_t peak_rgb = 0xEF4444u;
        if (peaking_idx == 2u) peak_rgb = 0xFACC15u;
        else if (peaking_idx == 3u) peak_rgb = 0xF8FAFCu;
        uint8_t prev_luma[FX6_W];
        for (int x = 0; x < FX6_W; x++) {
            uint32_t v = g_osd[x];
            if (!v) {
                prev_luma[x] = 0u;
            } else {
                uint32_t r = (v >> 16) & 0xffu, g = (v >> 8) & 0xffu, b = v & 0xffu;
                prev_luma[x] = (uint8_t)((54u * r + 183u * g + 19u * b) >> 8);
            }
        }
        for (int y = 1; y < FX6_H; y++) {
            uint32_t *row = g_osd + (unsigned long)y * (unsigned long)FX6_W;
            int left_luma = (int)prev_luma[0];
            for (int x = 1; x < FX6_W; x++) {
                uint32_t v = row[x];
                int cur_luma = 0;
                if (v) {
                    int r = (int)((v >> 16) & 0xffu);
                    int g = (int)((v >> 8) & 0xffu);
                    int b = (int)(v & 0xffu);
                    cur_luma = (54 * r + 183 * g + 19 * b) >> 8;
                }
                int up_luma = (int)prev_luma[x];
                int dv = (cur_luma >= up_luma) ? (cur_luma - up_luma) : (up_luma - cur_luma);
                int dh = (cur_luma >= left_luma) ? (cur_luma - left_luma) : (left_luma - cur_luma);
                prev_luma[x] = (uint8_t)cur_luma;
                left_luma = cur_luma;
                if (dv + dh >= 96) {
                    fx6_osd_blend_px(x, y, peak_rgb, 192u);
                }
            }
        }
    }

    /* 2. Cinema Line Zebra Overlay (45-deg diagonal stripes over highlight thresholds) */
    if (zebra_idx > 0u) {
        int luma_thresh = 178; /* 70% */
        if (zebra_idx == 2u) luma_thresh = 220;      /* 94%_SLog3 */
        else if (zebra_idx == 3u) luma_thresh = 242; /* 100% */
        for (int y = 0; y < FX6_H; y++) {
            uint32_t *row = g_osd + (unsigned long)y * (unsigned long)FX6_W;
            for (int x = 0; x < FX6_W; x++) {
                uint32_t v = row[x];
                if (!v) continue;
                int r = (int)((v >> 16) & 0xffu);
                int g = (int)((v >> 8) & 0xffu);
                int b = (int)(v & 0xffu);
                int luma = (54 * r + 183 * g + 19 * b) >> 8;
                if (luma >= luma_thresh) {
                    if (((x + y) & 7) < 3) {
                        fx6_osd_blend_px(x, y, 0xF59E0Bu, 176u);
                    } else {
                        fx6_osd_blend_px(x, y, 0x111827u, 112u);
                    }
                }
            }
        }
    }

    /* 3. Aspect Ratio Frame Guides (semi-transparent mattes + crisp lines + corner ticks) */
    if (aspect_idx == 1u) {
        /* 2.39:1 CinemaScope */
        fx6_osd_blend_rect(0, 0, FX6_W, 56, 0x000000u, 96u);
        fx6_osd_blend_rect(0, 484, FX6_W, FX6_H - 484, 0x000000u, 96u);
        fx6_osd_blend_rect(12, 56, 1000, 2, 0xE0F2FEu, 224u);
        fx6_osd_blend_rect(12, 482, 1000, 2, 0xE0F2FEu, 224u);
        fx6_draw_corner_ticks(12, 56, 1011, 483, 24, 3, 0x22D3EEu, 244u);
    } else if (aspect_idx == 2u) {
        /* 1.85:1 Flat Theatrical */
        fx6_osd_blend_rect(0, 0, 12, FX6_H, 0x000000u, 96u);
        fx6_osd_blend_rect(1012, 0, 12, FX6_H, 0x000000u, 96u);
        fx6_osd_blend_rect(12, 4, 1000, 2, 0xE0F2FEu, 224u);
        fx6_osd_blend_rect(12, 534, 1000, 2, 0xE0F2FEu, 224u);
        fx6_osd_blend_rect(12, 4, 2, 532, 0xE0F2FEu, 224u);
        fx6_osd_blend_rect(1010, 4, 2, 532, 0xE0F2FEu, 224u);
        fx6_draw_corner_ticks(12, 4, 1011, 535, 24, 3, 0x22D3EEu, 244u);
    } else if (aspect_idx == 3u) {
        /* 17:9 DCI 4K + 90% Safe Action Corner Ticks */
        fx6_osd_blend_rect(8, 4, 1008, 2, 0x38BDF8u, 224u);
        fx6_osd_blend_rect(8, 534, 1008, 2, 0x38BDF8u, 224u);
        fx6_osd_blend_rect(8, 4, 2, 532, 0x38BDF8u, 224u);
        fx6_osd_blend_rect(1014, 4, 2, 532, 0x38BDF8u, 224u);
        fx6_draw_corner_ticks(52, 27, 971, 512, 22, 2, 0xA7F3D0u, 216u);
    } else if (aspect_idx == 4u) {
        /* 9:16 Vertical Crop */
        fx6_osd_blend_rect(0, 0, 364, FX6_H, 0x000000u, 88u);
        fx6_osd_blend_rect(660, 0, FX6_W - 660, FX6_H, 0x000000u, 88u);
        fx6_osd_blend_rect(364, 8, 296, 2, 0xFDE047u, 232u);
        fx6_osd_blend_rect(364, 530, 296, 2, 0xFDE047u, 232u);
        fx6_osd_blend_rect(364, 8, 2, 524, 0xFDE047u, 232u);
        fx6_osd_blend_rect(658, 8, 2, 524, 0xFDE047u, 232u);
        fx6_draw_corner_ticks(364, 8, 659, 531, 22, 3, 0x22D3EEu, 244u);
    } else if (aspect_idx == 5u) {
        /* CenterCross + Rule-of-Thirds Ticks */
        fx6_osd_blend_rect(484, 269, 22, 2, 0x22D3EEu, 240u);
        fx6_osd_blend_rect(518, 269, 22, 2, 0x22D3EEu, 240u);
        fx6_osd_blend_rect(511, 242, 2, 22, 0x22D3EEu, 240u);
        fx6_osd_blend_rect(511, 276, 2, 22, 0x22D3EEu, 240u);
        fx6_osd_blend_rect(510, 268, 4, 4, 0xF59E0Bu, 240u);
        fx6_draw_corner_ticks(341, 180, 682, 360, 14, 2, 0xE0F2FEu, 176u);
    }

    /* 4. Cinema Line Assist Tools HUD Badge Strip (bottom-center, crystal clear) */
    int hx = 220, hy = 508, hw = 584, hh = 26;
    fx6_osd_fill_rect(hx, hy, hw, hh, 0xFF0B1220u);
    fx6_osd_border_rect(hx, hy, hw, hh, 0xFF22D3EEu);
    if (zebra_idx > 0u) {
        for (int zy = 0; zy < 16; zy++) {
            for (int zx = 0; zx < 18; zx++) {
                uint32_t zc = (((zx + zy) & 5) < 3) ? 0xFFF59E0Bu : 0xFF1F2937u;
                g_osd[(unsigned long)(hy + 5 + zy) * (unsigned long)FX6_W + (unsigned long)(hx + 6 + zx)] = zc;
            }
        }
    } else {
        fx6_osd_fill_rect(hx + 6, hy + 5, 18, 16, 0xFF1E293Bu);
    }
    if (peaking_idx > 0u) {
        uint32_t pc = (peaking_idx == 2u) ? 0xFFFACC15u : ((peaking_idx == 3u) ? 0xFFF8FAFCu : 0xFFEF4444u);
        fx6_osd_fill_rect(hx + 28, hy + 5, 10, 16, pc);
    } else {
        fx6_osd_fill_rect(hx + 28, hy + 5, 10, 16, 0xFF1E293Bu);
    }

    static const char * const k_aspect_lbl[6] = { "Off", "2.39:1", "1.85:1", "17:9", "9:16", "Cross" };
    static const char * const k_zebra_lbl[4]  = { "Off", "70%", "94%S3", "100%" };
    static const char * const k_peak_lbl[4]   = { "Off", "Red", "Yel", "Wht" };
    static const char * const k_desq_lbl[4]   = { "1.0x", "1.33x", "2.0x", "1.0x" };

    char assist_lbl[80];
    unsigned pos = 0u;
    pos = fx6_append_cstr(assist_lbl, pos, sizeof(assist_lbl), "MK:");
    pos = fx6_append_cstr(assist_lbl, pos, sizeof(assist_lbl), k_aspect_lbl[aspect_idx < 6u ? aspect_idx : 0u]);
    pos = fx6_append_cstr(assist_lbl, pos, sizeof(assist_lbl), "  ZEB:");
    pos = fx6_append_cstr(assist_lbl, pos, sizeof(assist_lbl), k_zebra_lbl[zebra_idx & 3u]);
    pos = fx6_append_cstr(assist_lbl, pos, sizeof(assist_lbl), "  PK:");
    pos = fx6_append_cstr(assist_lbl, pos, sizeof(assist_lbl), k_peak_lbl[peaking_idx & 3u]);
    pos = fx6_append_cstr(assist_lbl, pos, sizeof(assist_lbl), "  DSQ:");
    pos = fx6_append_cstr(assist_lbl, pos, sizeof(assist_lbl), k_desq_lbl[desqueeze_idx & 3u]);
    (void)pos;

    fx6_render_string_text_styled(appfw, hx + 44, hy + 2, hw - 52, 22, assist_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
}

static unsigned fx6_append_uint(char *dst, unsigned pos, unsigned cap, uint32_t val) {
    char tmp[16];
    int n = 0;
    if (val == 0u) {
        if (pos + 1u < cap) dst[pos++] = '0';
        dst[pos] = 0;
        return pos;
    }
    while (val > 0u && n < 15) {
        tmp[n++] = (char)('0' + (val % 10u));
        val /= 10u;
    }
    while (n > 0 && pos + 1u < cap) {
        dst[pos++] = tmp[--n];
    }
    dst[pos] = 0;
    return pos;
}

static unsigned fx6_append_2d(char *dst, unsigned pos, unsigned cap, uint32_t val) {
    if (pos + 2u >= cap) return pos;
    uint32_t v = val % 100u;
    dst[pos++] = (char)('0' + (v / 10u));
    dst[pos++] = (char)('0' + (v % 10u));
    dst[pos] = 0;
    return pos;
}

static void fx6_render_phase64_cine_exposure_overlay(uint64_t appfw, uint32_t page) {
    if (!g_osd || !(g_live_p64_flags & 0x80000000u)) return;

    static const uint32_t k_ei_800[13] = {
        200u, 250u, 320u, 400u, 500u, 640u, 800u, 1000u, 1250u, 1600u, 2000u, 2500u, 3200u
    };
    static const uint32_t k_ei_12800[13] = {
        3200u, 4000u, 5000u, 6400u, 8000u, 10000u, 12800u, 16000u, 20000u, 25600u, 32000u, 40000u, 51200u
    };
    static const uint32_t k_base_fps_x100[6] = { 2398u, 2400u, 2500u, 2997u, 5000u, 5994u };
    static const char * const k_base_fps_lbl[6] = { "23.98p", "24.00p", "25.00p", "29.97p", "50.00p", "59.94p" };

    uint32_t base_high    = g_live_p64_flags & 1u;
    uint32_t ei_step      = (g_live_p64_flags >> 1) & 0x0fu;
    if (ei_step > 12u) ei_step = 6u;
    uint32_t shutter_mode = (g_live_p64_flags >> 5) & 0x03u;
    uint32_t sq_on        = (g_live_p64_flags >> 7) & 1u;
    uint32_t base_fps_idx = (g_live_p64_flags >> 8) & 0x07u;
    if (base_fps_idx > 5u) base_fps_idx = 0u;
    uint32_t rec_on       = (g_live_p64_flags >> 11) & 1u;
    uint32_t tally_mode   = (g_live_p64_flags >> 12) & 0x03u;
    uint32_t wired_io     = (g_live_p64_flags >> 14) & 0x03u;

    uint32_t shutter_val  = g_live_p64_shutter_sq & 0xfffffu;
    uint32_t sq_fps       = (g_live_p64_shutter_sq >> 20) & 0xffu;
    if (sq_fps < 1u || sq_fps > 240u) sq_fps = 24u;

    uint32_t p = page % 25u;
    int is_shooting_page = (p <= 3u || p == 6u || p == 16u || p == 17u);

    if (!is_shooting_page) {
        if (!rec_on && !sq_on && wired_io == 0u) return;
        int bx = 736, by = 10, bw = 276, bh = 26;
        uint32_t bg = rec_on ? 0xFF7F1D1Du : 0xFF0F172Au;
        uint32_t bd = rec_on ? 0xFFEF4444u : (sq_on ? 0xFFF59E0Bu : 0xFF22D3EEu);
        fx6_osd_fill_rect(bx, by, bw, bh, bg);
        fx6_osd_border_rect(bx, by, bw, bh, bd);
        uint32_t dot_c = rec_on ? ((tally_mode == 3u) ? 0xFF4B5563u : 0xFFFF2D20u) : 0xFF10B981u;
        fx6_osd_fill_rect(bx + 6, by + 7, 12, 12, dot_c);
        char mini_lbl[48];
        unsigned mp = 0u;
        mp = fx6_append_cstr(mini_lbl, mp, sizeof(mini_lbl), rec_on ? "REC " : "STBY ");
        if (sq_on) {
            mp = fx6_append_cstr(mini_lbl, mp, sizeof(mini_lbl), "S&Q");
            mp = fx6_append_uint(mini_lbl, mp, sizeof(mini_lbl), sq_fps);
            mp = fx6_append_cstr(mini_lbl, mp, sizeof(mini_lbl), " ");
        }
        if (wired_io == 1u) mp = fx6_append_cstr(mini_lbl, mp, sizeof(mini_lbl), "PTP-IP");
        else if (wired_io == 2u) mp = fx6_append_cstr(mini_lbl, mp, sizeof(mini_lbl), "RAW16");
        (void)mp;
        fx6_render_string_text_styled(appfw, bx + 22, by + 2, bw - 26, 22, mini_lbl,
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
        return;
    }

    int bx = 12;
    int by = (p <= 3u) ? 478 : 10;
    int bw = 1000;
    int bh = 26;

    fx6_osd_fill_rect(bx, by, bw, bh, 0xFF0A0F1Au);
    fx6_osd_border_rect(bx, by, bw, bh, rec_on ? 0xFFEF4444u : 0xFF334155u);

    /* Pill 1: REC / STBY + Tally Lamp Indicator + Live TC */
    int p1x = bx + 4, p1w = 172;
    uint32_t p1_bg = rec_on ? 0xFF7F1D1Du : 0xFF064E3Bu;
    uint32_t p1_bd = rec_on ? 0xFFEF4444u : 0xFF10B981u;
    fx6_osd_fill_rect(p1x, by + 2, p1w, bh - 4, p1_bg);
    fx6_osd_border_rect(p1x, by + 2, p1w, bh - 4, p1_bd);

    uint32_t front_lit = (rec_on && (tally_mode == 0u || tally_mode == 1u)) ? 1u : 0u;
    uint32_t rear_lit  = (rec_on && (tally_mode == 0u || tally_mode == 2u)) ? 1u : 0u;
    fx6_osd_fill_rect(p1x + 5, by + 6, 6, 14, front_lit ? 0xFFFF2D20u : (rec_on ? 0xFF374151u : 0xFF10B981u));
    fx6_osd_fill_rect(p1x + 13, by + 6, 6, 14, rear_lit ? 0xFFFF6B4Au : (rec_on ? 0xFF374151u : 0xFF059669u));

    char rec_lbl[36];
    unsigned rp = 0u;
    if (rec_on) {
        uint32_t f_rate = (base_fps_idx == 2u || base_fps_idx == 4u) ? 25u : 24u;
        uint32_t tc = g_live_p64_tc;
        uint32_t ff = tc % f_rate;
        uint32_t tot_s = tc / f_rate;
        uint32_t ss = tot_s % 60u;
        uint32_t mm = (tot_s / 60u) % 60u;
        rp = fx6_append_cstr(rec_lbl, rp, sizeof(rec_lbl), "REC ");
        rp = fx6_append_2d(rec_lbl, rp, sizeof(rec_lbl), mm);
        rp = fx6_append_cstr(rec_lbl, rp, sizeof(rec_lbl), ":");
        rp = fx6_append_2d(rec_lbl, rp, sizeof(rec_lbl), ss);
        rp = fx6_append_cstr(rec_lbl, rp, sizeof(rec_lbl), ":");
        rp = fx6_append_2d(rec_lbl, rp, sizeof(rec_lbl), ff);
        if (tally_mode == 3u) rp = fx6_append_cstr(rec_lbl, rp, sizeof(rec_lbl), " STL");
    } else {
        rp = fx6_append_cstr(rec_lbl, rp, sizeof(rec_lbl), "STBY");
        if (tally_mode == 3u) rp = fx6_append_cstr(rec_lbl, rp, sizeof(rec_lbl), " [T-OFF]");
        else if (tally_mode == 1u) rp = fx6_append_cstr(rec_lbl, rp, sizeof(rec_lbl), " [F-TLY]");
        else if (tally_mode == 2u) rp = fx6_append_cstr(rec_lbl, rp, sizeof(rec_lbl), " [R-TLY]");
    }
    (void)rp;
    fx6_render_string_text_styled(appfw, p1x + 22, by + 2, p1w - 24, 22, rec_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);

    /* Pill 2: Cine EI + Base ISO + Dynamic Latitude (+over/-under stops) */
    int p2x = p1x + p1w + 4, p2w = 236;
    fx6_osd_fill_rect(p2x, by + 2, p2w, bh - 4, 0xFF111827u);
    fx6_osd_border_rect(p2x, by + 2, p2w, bh - 4, base_high ? 0xFFF59E0Bu : 0xFF38BDF8u);

    uint32_t ei_val = base_high ? k_ei_12800[ei_step] : k_ei_800[ei_step];
    int step_delta = (int)ei_step - 6;
    int over_x10 = 60 + (step_delta * 10 + (step_delta >= 0 ? 1 : -1)) / 3;
    int under_x10 = 140 - over_x10;
    char ei_lbl[44];
    unsigned ep = 0u;
    ep = fx6_append_uint(ei_lbl, ep, sizeof(ei_lbl), ei_val);
    ep = fx6_append_cstr(ei_lbl, ep, sizeof(ei_lbl), "EI (B");
    ep = fx6_append_cstr(ei_lbl, ep, sizeof(ei_lbl), base_high ? "12800 +" : "800 +");
    ep = fx6_append_uint(ei_lbl, ep, sizeof(ei_lbl), (uint32_t)(over_x10 / 10));
    if ((over_x10 % 10) != 0) {
        ep = fx6_append_cstr(ei_lbl, ep, sizeof(ei_lbl), ".");
        ep = fx6_append_uint(ei_lbl, ep, sizeof(ei_lbl), (uint32_t)(over_x10 % 10));
    }
    ep = fx6_append_cstr(ei_lbl, ep, sizeof(ei_lbl), "/-");
    ep = fx6_append_uint(ei_lbl, ep, sizeof(ei_lbl), (uint32_t)(under_x10 / 10));
    if ((under_x10 % 10) != 0) {
        ep = fx6_append_cstr(ei_lbl, ep, sizeof(ei_lbl), ".");
        ep = fx6_append_uint(ei_lbl, ep, sizeof(ei_lbl), (uint32_t)(under_x10 % 10));
    }
    ep = fx6_append_cstr(ei_lbl, ep, sizeof(ei_lbl), ")");
    (void)ep;
    fx6_render_string_text_styled(appfw, p2x + 5, by + 2, p2w - 8, 22, ei_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);

    /* Pill 3: Shutter Angle / Speed / ECS LED Anti-Flicker */
    int p3x = p2x + p2w + 4, p3w = 142;
    fx6_osd_fill_rect(p3x, by + 2, p3w, bh - 4, (shutter_mode == 2u) ? 0xFF1E1B4Bu : 0xFF111827u);
    fx6_osd_border_rect(p3x, by + 2, p3w, bh - 4, (shutter_mode == 2u) ? 0xFFF59E0Bu : 0xFF475569u);
    char sh_lbl[32];
    unsigned sp = 0u;
    if (shutter_mode == 1u) {
        sp = fx6_append_cstr(sh_lbl, sp, sizeof(sh_lbl), "1/");
        sp = fx6_append_uint(sh_lbl, sp, sizeof(sh_lbl), shutter_val ? shutter_val : 48u);
    } else if (shutter_mode == 2u) {
        uint32_t hz_i = shutter_val / 100u;
        uint32_t hz_f = (shutter_val % 100u) / 10u;
        sp = fx6_append_cstr(sh_lbl, sp, sizeof(sh_lbl), "ECS ");
        sp = fx6_append_uint(sh_lbl, sp, sizeof(sh_lbl), hz_i);
        sp = fx6_append_cstr(sh_lbl, sp, sizeof(sh_lbl), ".");
        sp = fx6_append_uint(sh_lbl, sp, sizeof(sh_lbl), hz_f);
        sp = fx6_append_cstr(sh_lbl, sp, sizeof(sh_lbl), "Hz");
    } else {
        uint32_t deg_i = shutter_val / 10u;
        uint32_t deg_f = shutter_val % 10u;
        sp = fx6_append_uint(sh_lbl, sp, sizeof(sh_lbl), deg_i);
        sp = fx6_append_cstr(sh_lbl, sp, sizeof(sh_lbl), ".");
        sp = fx6_append_uint(sh_lbl, sp, sizeof(sh_lbl), deg_f);
        sp = fx6_append_cstr(sh_lbl, sp, sizeof(sh_lbl), "\xc2\xb0");
    }
    (void)sp;
    fx6_render_string_text_styled(appfw, p3x + 6, by + 2, p3w - 10, 22, sh_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);

    /* Pill 4: S&Q (1-240fps) + Audio Mute Indicator / P4 ND=Clear Lock */
    int p4x = p3x + p3w + 4, p4w = 248;
    fx6_osd_fill_rect(p4x, by + 2, p4w, bh - 4, sq_on ? 0xFF78350Fu : 0xFF111827u);
    fx6_osd_border_rect(p4x, by + 2, p4w, bh - 4, sq_on ? 0xFFF59E0Bu : 0xFF475569u);
    char sq_lbl[48];
    unsigned qp = 0u;
    if (sq_on) {
        uint32_t b_x100 = k_base_fps_x100[base_fps_idx];
        uint32_t ratio_x10 = (sq_fps * 1000u + (b_x100 / 2u)) / b_x100;
        qp = fx6_append_cstr(sq_lbl, qp, sizeof(sq_lbl), "S&Q ");
        qp = fx6_append_uint(sq_lbl, qp, sizeof(sq_lbl), sq_fps);
        qp = fx6_append_cstr(sq_lbl, qp, sizeof(sq_lbl), "fps (");
        qp = fx6_append_uint(sq_lbl, qp, sizeof(sq_lbl), ratio_x10 / 10u);
        qp = fx6_append_cstr(sq_lbl, qp, sizeof(sq_lbl), ".");
        qp = fx6_append_uint(sq_lbl, qp, sizeof(sq_lbl), ratio_x10 % 10u);
        qp = fx6_append_cstr(sq_lbl, qp, sizeof(sq_lbl), "x) [CH1-4 MUTE]");
    } else {
        qp = fx6_append_cstr(sq_lbl, qp, sizeof(sq_lbl), k_base_fps_lbl[base_fps_idx]);
        qp = fx6_append_cstr(sq_lbl, qp, sizeof(sq_lbl), " NORM [P4:ND-CLR]");
    }
    (void)qp;
    fx6_render_string_text_styled(appfw, p4x + 5, by + 2, p4w - 8, 22, sq_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);

    /* Pill 5: Wired I/O Mode + P12 Airplane-Mode RF-OFF Safety */
    int p5x = p4x + p4w + 4, p5w = (bx + bw - 4) - p5x;
    uint32_t p5_bg = (wired_io == 2u) ? 0xFF4C1D95u : ((wired_io == 1u) ? 0xFF0E7490u : 0xFF111827u);
    uint32_t p5_bd = (wired_io == 2u) ? 0xFFA78BFAu : ((wired_io == 1u) ? 0xFF22D3EEu : 0xFF475569u);
    fx6_osd_fill_rect(p5x, by + 2, p5w, bh - 4, p5_bg);
    fx6_osd_border_rect(p5x, by + 2, p5w, bh - 4, p5_bd);
    const char *io_lbl = (wired_io == 2u)
        ? "[HDMI RAW16 4.2K]"
        : ((wired_io == 1u) ? "[LAN PTP-IP P12-SAFE]" : "I/O:OFF [P12 RF-OFF]");
    fx6_render_string_text_styled(appfw, p5x + 5, by + 2, p5w - 8, 22, io_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
}

static unsigned fx6_append_3d(char *dst, unsigned pos, unsigned cap, uint32_t val) {
    if (pos + 3u >= cap) return pos;
    uint32_t v = val % 1000u;
    dst[pos++] = (char)('0' + (v / 100u));
    dst[pos++] = (char)('0' + ((v / 10u) % 10u));
    dst[pos++] = (char)('0' + (v % 10u));
    dst[pos] = 0;
    return pos;
}

static void fx6_render_phase73_wb_look_dualslot_overlay(uint64_t appfw, uint32_t page) {
    if (!g_osd || !(g_live_p73_wb_look & 0x80000000u)) return;

    static const char * const k_look_lbl[7] = {
        "S-Cinetone", "S-Log3.Cine", "S-Log3", "ITU709", "709(800%)", "HLG Live", "User 3D LUT"
    };
    static const char * const k_slot_lbl[4] = {
        "[A+B SIMUL] ", "[A->B RELAY] ", "[A|B SORT] ", "[SLOT-A] "
    };
    static const char k_pos_ch[4] = { 'C', 'L', 'R', 'C' };

    uint32_t wb_mode_idx  = g_live_p73_wb_look & 0x07u;
    uint32_t kelvin       = (g_live_p73_wb_look >> 3) & 0x3fffu;
    if (kelvin < 2000u || kelvin > 15000u) kelvin = 5600u;
    int tint_gm           = (int)((g_live_p73_wb_look >> 17) & 0xffu) - 99;
    if (tint_gm < -99) tint_gm = -99;
    if (tint_gm > 99) tint_gm = 99;
    uint32_t shockless    = (g_live_p73_wb_look >> 25) & 0x03u;
    uint32_t look_idx     = (g_live_p73_wb_look >> 27) & 0x07u;
    if (look_idx > 6u) look_idx = 0u;

    uint32_t cam_id_idx   = g_live_p73_media_clip & 0x1fu;
    if (cam_id_idx > 25u) cam_id_idx = 0u;
    uint32_t reel_num     = (g_live_p73_media_clip >> 5) & 0x3ffu;
    if (reel_num < 1u || reel_num > 999u) reel_num = 1u;
    uint32_t cam_pos_idx  = (g_live_p73_media_clip >> 15) & 0x03u;
    uint32_t clip_seq     = (g_live_p73_media_clip >> 17) & 0x3ffu;
    if (clip_seq < 1u || clip_seq > 999u) clip_seq = 1u;
    uint32_t dual_slot    = (g_live_p73_media_clip >> 27) & 0x03u;
    uint32_t proxy_mode   = (g_live_p73_media_clip >> 29) & 0x03u;
    uint32_t proxy_eff    = (g_live_p73_media_clip >> 31) & 1u;
    uint32_t sq_susp      = ((g_live_p73_flags2 & 1u) || ((g_live_p64_flags >> 7) & 1u)) ? 1u : 0u;
    uint32_t lut_slot     = (g_live_p73_flags2 >> 1) & 0x07u;

    char wb_lbl[64];
    unsigned wp = 0u;
    wp = fx6_append_uint(wb_lbl, wp, sizeof(wb_lbl), kelvin);
    wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), "K");
    if (tint_gm < 0) {
        wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), "-");
        wp = fx6_append_uint(wb_lbl, wp, sizeof(wb_lbl), (uint32_t)(-tint_gm));
    } else {
        wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), "+");
        wp = fx6_append_uint(wb_lbl, wp, sizeof(wb_lbl), (uint32_t)tint_gm);
    }
    wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), " ");
    if (look_idx == 6u && g_live_lut_name[0]) {
        wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), "Usr");
        wp = fx6_append_uint(wb_lbl, wp, sizeof(wb_lbl), lut_slot ? lut_slot : 1u);
        wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), ":");
        wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), g_live_lut_name);
    } else {
        wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), k_look_lbl[look_idx]);
    }
    if (wb_mode_idx == 3u) wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), " [MEM-A]");
    else if (wb_mode_idx == 4u) wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), " [MEM-B]");
    else if (wb_mode_idx == 5u) {
        if (shockless > 0u) {
            wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), " [ATW:S");
            wp = fx6_append_uint(wb_lbl, wp, sizeof(wb_lbl), shockless);
            wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), "]");
        } else {
            wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), " [ATW]");
        }
    } else if (shockless > 0u) {
        wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), " [SL:");
        wp = fx6_append_uint(wb_lbl, wp, sizeof(wb_lbl), shockless);
        wp = fx6_append_cstr(wb_lbl, wp, sizeof(wb_lbl), "]");
    }
    (void)wp;

    char clip_lbl[64];
    unsigned cp = 0u;
    cp = fx6_append_cstr(clip_lbl, cp, sizeof(clip_lbl), k_slot_lbl[dual_slot]);
    if (cp + 1u < sizeof(clip_lbl)) {
        clip_lbl[cp++] = (char)('A' + cam_id_idx);
        clip_lbl[cp] = 0;
    }
    cp = fx6_append_3d(clip_lbl, cp, sizeof(clip_lbl), reel_num);
    if (cp + 1u < sizeof(clip_lbl)) {
        clip_lbl[cp++] = k_pos_ch[cam_pos_idx & 3u];
        clip_lbl[cp] = 0;
    }
    cp = fx6_append_3d(clip_lbl, cp, sizeof(clip_lbl), clip_seq);
    if (sq_susp) {
        cp = fx6_append_cstr(clip_lbl, cp, sizeof(clip_lbl), " PRX:OFF(S&Q)");
    } else if (proxy_eff && proxy_mode > 0u) {
        cp = fx6_append_cstr(clip_lbl, cp, sizeof(clip_lbl), " PRX");
    } else {
        cp = fx6_append_cstr(clip_lbl, cp, sizeof(clip_lbl), " PRX:OFF");
    }
    (void)cp;

    uint32_t p = page % 25u;
    int is_shooting_page = (p <= 3u || p == 6u || p == 16u || p == 17u);
    if (!is_shooting_page) {
        if (g_live_p73_wb_look == 0xc0c6af02u && g_live_p73_media_clip == 0xa0020020u && !sq_susp) {
            return;
        }
        int bx = 12, by = 10, bw = 460, bh = 26;
        fx6_osd_fill_rect(bx, by, bw, bh, 0xFF0F172Au);
        fx6_osd_border_rect(bx, by, bw, bh, 0xFF38BDF8u);
        fx6_render_string_text_styled(appfw, bx + 6, by + 2, bw - 12, 22, wb_lbl,
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
        return;
    }

    uint32_t p56_active = ((g_live_p40_flags >> 12) & 0x3ffu);
    int by = 508;
    if (p56_active) {
        by = (p <= 3u) ? 448 : 478;
    }
    int bh = 26;

    /* Pill A: White Balance (Kelvin + Tint + Shockless) + Base Look */
    int pax = 12, paw = 476;
    uint32_t wb_bg = (look_idx == 1u || look_idx == 2u) ? 0xFF1E1B4Bu : ((look_idx == 6u) ? 0xFF134E4Au : 0xFF0F172Au);
    uint32_t wb_bd = (wb_mode_idx == 5u) ? 0xFFF59E0Bu : ((look_idx == 1u || look_idx == 2u) ? 0xFF818CF8u : 0xFF38BDF8u);
    fx6_osd_fill_rect(pax, by, paw, bh, wb_bg);
    fx6_osd_border_rect(pax, by, paw, bh, wb_bd);
    uint32_t kelvin_dot = (kelvin <= 3600u) ? 0xFFF59E0Bu : ((kelvin >= 6000u) ? 0xFF60A5FAu : 0xFFF8FAFCu);
    fx6_osd_fill_rect(pax + 6, by + 7, 10, 12, kelvin_dot);
    fx6_render_string_text_styled(appfw, pax + 22, by + 2, paw - 28, 22, wb_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);

    /* Pill B: Dual-Slot Mode + Cinema Line Clip ID + Proxy Status */
    int pbx = 496, pbw = 516;
    uint32_t med_bg = sq_susp ? 0xFF451A03u : ((dual_slot == 1u) ? 0xFF0C4A6Eu : 0xFF0F172Au);
    uint32_t med_bd = sq_susp ? 0xFFF59E0Bu : (proxy_eff ? 0xFF10B981u : 0xFF64748Bu);
    fx6_osd_fill_rect(pbx, by, pbw, bh, med_bg);
    fx6_osd_border_rect(pbx, by, pbw, bh, med_bd);
    fx6_osd_fill_rect(pbx + 6, by + 7, 10, 12, proxy_eff ? 0xFF10B981u : (sq_susp ? 0xFFF59E0Bu : 0xFF475569u));
    fx6_render_string_text_styled(appfw, pbx + 22, by + 2, pbw - 28, 22, clip_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
}

static void fx6_render_phase81_touchaf_falsecolor_ciz_overlay(uint64_t appfw, uint32_t page) {
    if (!g_osd || !(g_live_p81_ciz_flags & 0x80000000u)) return;

    uint32_t af_mode    = g_live_p81_touch_af & 0x03u;
    uint32_t touch_x    = (g_live_p81_touch_af >> 2) & 0x3ffu;
    uint32_t touch_y    = (g_live_p81_touch_af >> 12) & 0x3ffu;
    uint32_t pdaf_idx   = (g_live_p81_touch_af >> 22) & 0x3ffu;
    if (touch_x > 959u) touch_x = 959u;
    if (touch_y > 539u) touch_y = 539u;
    if (pdaf_idx > 626u) pdaf_idx = 626u;

    uint32_t pdaf_col   = g_live_p81_pdaf_mag_fc & 0x3fu;
    uint32_t pdaf_row   = (g_live_p81_pdaf_mag_fc >> 6) & 0x1fu;
    uint32_t mag_idx    = (g_live_p81_pdaf_mag_fc >> 11) & 0x03u;
    uint32_t fc_mode    = (g_live_p81_pdaf_mag_fc >> 13) & 0x03u;
    uint32_t clean_hdmi = (g_live_p81_pdaf_mag_fc >> 15) & 0x01u;
    uint32_t eff_ciz    = (g_live_p81_pdaf_mag_fc >> 16) & 0xffu;
    if (pdaf_col > 32u) pdaf_col = 32u;
    if (pdaf_row > 18u) pdaf_row = 18u;
    if (eff_ciz < 100u || eff_ciz > 200u) eff_ciz = 100u;

    uint32_t spd         = g_live_p81_ciz_flags & 0x0fu;
    uint32_t ciz_excl    = (g_live_p81_ciz_flags >> 5) & 0x01u;
    uint32_t zeb100_warn = (g_live_p81_ciz_flags >> 7) & 0x01u;
    if (spd < 1u || spd > 8u) spd = 4u;

    if (af_mode == 0u && mag_idx == 0u && fc_mode == 0u && eff_ciz <= 100u && !ciz_excl && !zeb100_warn) {
        return;
    }

    uint32_t p = page % 25u;
    int is_shooting_page = (p <= 3u || p == 6u || p == 16u || p == 17u);

    /* 1. S-Log3 False Color / EL-Zone pixel colorization + Right-side IRE/EV Legend Bar */
    if (fc_mode > 0u) {
        if (g_syms.processCommands) g_syms.processCommands(0);
        int fc_y0 = 46;
        int fc_y1 = is_shooting_page ? 444 : 504;
        int fc_x0 = 16;
        int fc_x1 = 950;
        for (int y = fc_y0; y < fc_y1; y++) {
            uint32_t *row = g_osd + (unsigned long)y * (unsigned long)FX6_W;
            for (int x = fc_x0; x < fc_x1; x++) {
                uint32_t v = row[x];
                if (!v) continue;
                uint32_t r = (v >> 16) & 0xffu;
                uint32_t g = (v >> 8) & 0xffu;
                uint32_t b = v & 0xffu;
                uint32_t luma = (54u * r + 183u * g + 19u * b) >> 8;
                uint32_t ire_x10 = (luma * 1090u) / 255u;
                uint32_t fc_rgb = 0x2563EBu;
                if (fc_mode == 1u) {
                    /* Sony S-Log3 IRE bands: 3.5% purple, 41% green, 52% pink, 94% red */
                    if (ire_x10 <= 35u)       fc_rgb = 0x7E22CEu;
                    else if (ire_x10 <= 200u) fc_rgb = 0x2563EBu;
                    else if (ire_x10 <= 380u) fc_rgb = 0x06B6D4u;
                    else if (ire_x10 <= 440u) fc_rgb = 0x22C55Eu;
                    else if (ire_x10 <= 560u) fc_rgb = 0xF472B6u;
                    else if (ire_x10 <= 780u) fc_rgb = 0xFACC15u;
                    else if (ire_x10 < 940u)  fc_rgb = 0xF97316u;
                    else                      fc_rgb = 0xEF4444u;
                } else {
                    /* EL-Zone Stop-Based bands */
                    if (ire_x10 <= 80u)       fc_rgb = 0x6D28D9u;
                    else if (ire_x10 <= 260u) fc_rgb = 0x0284C7u;
                    else if (ire_x10 <= 450u) fc_rgb = 0x16A34Au;
                    else if (ire_x10 <= 580u) fc_rgb = 0xEC4899u;
                    else if (ire_x10 < 900u)  fc_rgb = 0xF59E0Bu;
                    else                      fc_rgb = 0xDC2626u;
                }
                fx6_osd_blend_px(x, y, fc_rgb, 148u);
            }
        }

        /* Right-side IRE / EV Legend Bar */
        int lx = 956, ly = 68, lw = 60, lh = 354;
        fx6_osd_fill_rect(lx, ly, lw, lh, 0xFF0A0F1Au);
        fx6_osd_border_rect(lx, ly, lw, lh, (fc_mode == 1u) ? 0xFFA855F7u : 0xFFEC4899u);
        fx6_render_string_text_styled(appfw, lx + 4, ly + 4, lw - 8, 20,
                                      (fc_mode == 1u) ? "S3 IRE" : "EL-ZN",
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
        static const uint32_t k_fc_cols[7] = {
            0xFFEF4444u, 0xFFFACC15u, 0xFFF472B6u, 0xFF22C55Eu, 0xFF06B6D4u, 0xFF2563EBu, 0xFF7E22CEu
        };
        static const char * const k_s3_lbls[7] = {
            "94%", "70%", "52%", "41%", "25%", "10%", "3.5"
        };
        static const char * const k_el_lbls[7] = {
            "+5EV", "+3EV", "+1EV", " 0EV", "-2EV", "-3EV", "-5EV"
        };
        for (int b = 0; b < 7; b++) {
            int by = ly + 30 + b * 45;
            fx6_osd_fill_rect(lx + 5, by, 14, 38, k_fc_cols[b]);
            fx6_osd_border_rect(lx + 5, by, 14, 38, 0xFFE5E7EBu);
            fx6_render_string_text_styled(appfw, lx + 21, by + 8, lw - 24, 22,
                                          (fc_mode == 1u) ? k_s3_lbls[b] : k_el_lbls[b],
                                          0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
        }
    }

    /* 2. Focus Magnifier Orange Corner Border + [MAG x4.0] Badge (HDMI Clean Feed 1.0x) */
    int badge_y = 48;
    if (mag_idx > 0u) {
        fx6_draw_corner_ticks(16, 48, 948, 440, 34, 4, 0xF97316u, 248u);
        fx6_osd_border_rect(16, 48, 933, 393, 0xFFF97316u);
        int mx = 22, my = badge_y, mw = 212, mh = 26;
        fx6_osd_fill_rect(mx, my, mw, mh, 0xFF7C2D12u);
        fx6_osd_border_rect(mx, my, mw, mh, 0xFFF97316u);
        const char *mag_lbl = (mag_idx >= 2u)
            ? (clean_hdmi ? "[MAG x4.0] HDMI:1x" : "[MAG x4.0]")
            : (clean_hdmi ? "[MAG x2.0] HDMI:1x" : "[MAG x2.0]");
        fx6_render_string_text_styled(appfw, mx + 6, my + 2, mw - 12, 22, mag_lbl,
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
        badge_y += 30;
    }

    /* 3. Clear Image Zoom [CIZ 1.40x] Zoom Bar Badge (or Exclusion Clamp Badge) */
    if (eff_ciz > 100u || ciz_excl) {
        int cx = 22, cy = badge_y, cw = 220, ch = 26;
        uint32_t c_bg = ciz_excl ? 0xFF78350Fu : 0xFF0E7490u;
        uint32_t c_bd = ciz_excl ? 0xFFF59E0Bu : 0xFF22D3EEu;
        fx6_osd_fill_rect(cx, cy, cw, ch, c_bg);
        fx6_osd_border_rect(cx, cy, cw, ch, c_bd);

        /* Proportional CIZ bar 1.00x .. 2.00x */
        int bar_x = cx + 6, bar_y = cy + 19, bar_w = cw - 12;
        fx6_osd_fill_rect(bar_x, bar_y, bar_w, 4, 0xFF0F172Au);
        int fill_w = (int)(((eff_ciz - 100u) * (uint32_t)bar_w) / 100u);
        if (fill_w < 4) fill_w = 4;
        if (fill_w > bar_w) fill_w = bar_w;
        fx6_osd_fill_rect(bar_x, bar_y, fill_w, 4, ciz_excl ? 0xFFF59E0Bu : 0xFF67E8F9u);

        char ciz_lbl[40];
        unsigned cp = 0u;
        cp = fx6_append_cstr(ciz_lbl, cp, sizeof(ciz_lbl), "[CIZ ");
        cp = fx6_append_uint(ciz_lbl, cp, sizeof(ciz_lbl), eff_ciz / 100u);
        cp = fx6_append_cstr(ciz_lbl, cp, sizeof(ciz_lbl), ".");
        cp = fx6_append_2d(ciz_lbl, cp, sizeof(ciz_lbl), eff_ciz % 100u);
        cp = fx6_append_cstr(ciz_lbl, cp, sizeof(ciz_lbl), "x]");
        if (ciz_excl) {
            cp = fx6_append_cstr(ciz_lbl, cp, sizeof(ciz_lbl), " EXCL");
        } else {
            cp = fx6_append_cstr(ciz_lbl, cp, sizeof(ciz_lbl), " S");
            cp = fx6_append_uint(ciz_lbl, cp, sizeof(ciz_lbl), spd);
        }
        (void)cp;
        fx6_render_string_text_styled(appfw, cx + 6, cy + 1, cw - 12, 18, ciz_lbl,
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
        badge_y += 30;
    }

    /* 4. S-Log3 + Zebra 100% Clip Warning Badge */
    if (zeb100_warn) {
        int wx = 22, wy = badge_y, ww = 290, wh = 24;
        fx6_osd_fill_rect(wx, wy, ww, wh, 0xFF7F1D1Du);
        fx6_osd_border_rect(wx, wy, ww, wh, 0xFFEF4444u);
        fx6_render_string_text_styled(appfw, wx + 6, wy + 2, ww - 12, 20,
                                      "WARN: S-Log3 ZEB100% CLIP@94%",
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
    }

    /* 5. Touch Tracking AF Double-Frame Reticle + PDAF Cell Badge */
    if (af_mode > 0u) {
        int rx = (int)((touch_x * 1024u) / 960u);
        int ry = (int)touch_y;
        if (rx < 44) rx = 44;
        if (rx > 940) rx = 940;
        if (ry < 44) ry = 44;
        if (ry > 438) ry = 438;

        int rw = 36, rh = 28;
        int rw2 = 26, rh2 = 20;
        uint32_t ret_rgb  = (af_mode == 2u) ? 0x22C55Eu : 0xF8FAFCu;
        uint32_t ret_in   = (af_mode == 2u) ? 0x86EFACu : 0xCBD5E1u;
        uint32_t ret_argb = 0xFF000000u | ret_rgb;

        /* Outer bracket corners */
        fx6_draw_corner_ticks(rx - rw, ry - rh, rx + rw, ry + rh, 14, 3, ret_rgb, 252u);
        /* Inner tracking double-frame corners */
        fx6_draw_corner_ticks(rx - rw2, ry - rh2, rx + rw2, ry + rh2, 10, 2, ret_in, 240u);
        /* Crisp center crosshairs */
        fx6_osd_fill_rect(rx - 6, ry, 13, 2, ret_argb);
        fx6_osd_fill_rect(rx, ry - 6, 2, 13, ret_argb);

        /* PDAF 33x19 Cell Badge right below (or above) reticle */
        int bx = rx - 82;
        if (bx < 16) bx = 16;
        if (bx + 166 > 952) bx = 952 - 166;
        int by = (ry + rh + 30 <= 444) ? (ry + rh + 4) : (ry - rh - 26);
        int bw = 166, bh = 22;
        fx6_osd_fill_rect(bx, by, bw, bh, (af_mode == 2u) ? 0xFF052E16u : 0xFF0F172Au);
        fx6_osd_border_rect(bx, by, bw, bh, ret_argb);

        char af_lbl[40];
        unsigned ap = 0u;
        ap = fx6_append_cstr(af_lbl, ap, sizeof(af_lbl), (af_mode == 2u) ? "TRK #" : "AF #");
        ap = fx6_append_uint(af_lbl, ap, sizeof(af_lbl), pdaf_idx);
        ap = fx6_append_cstr(af_lbl, ap, sizeof(af_lbl), " (");
        ap = fx6_append_uint(af_lbl, ap, sizeof(af_lbl), pdaf_col);
        ap = fx6_append_cstr(af_lbl, ap, sizeof(af_lbl), ",");
        ap = fx6_append_uint(af_lbl, ap, sizeof(af_lbl), pdaf_row);
        ap = fx6_append_cstr(af_lbl, ap, sizeof(af_lbl), ")");
        (void)ap;
        fx6_render_string_text_styled(appfw, bx + 5, by + 1, bw - 10, 20, af_lbl,
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
    }
}

static unsigned fx6_append_hex8(char *dst, unsigned pos, unsigned cap, uint32_t val) {
    static const char k_hex[16] = "0123456789ABCDEF";
    if (pos + 11u >= cap) return pos;
    for (int sh = 28; sh >= 0; sh -= 4) {
        dst[pos++] = k_hex[(val >> (unsigned)sh) & 0x0fu];
        if (sh == 24 || sh == 16 || sh == 8) {
            dst[pos++] = ':';
        }
    }
    dst[pos] = 0;
    return pos;
}

static void fx6_render_phase88_shotmark_iris_overlay(uint64_t appfw, uint32_t page) {
    if (!g_osd || !(g_live_p88_iris_audio & 0x80000000u)) return;

    uint32_t sm_total   = g_live_p88_shotmark & 0x7fu;
    uint32_t sm1_cnt    = (g_live_p88_shotmark >> 7) & 0x7fu;
    uint32_t sm2_cnt    = (g_live_p88_shotmark >> 14) & 0x7fu;
    uint32_t last_type  = (g_live_p88_shotmark >> 21) & 0x03u;
    uint32_t last_frame = (g_live_p88_shotmark >> 23) & 0x1ffu;

    uint32_t iris_x100   = g_live_p88_iris_audio & 0xfffu;
    if (iris_x100 < 140u || iris_x100 > 2200u) iris_x100 = 280u;
    uint32_t meter       = (g_live_p88_iris_audio >> 12) & 0x03u;
    uint32_t ch34_pad20  = (g_live_p88_iris_audio >> 22) & 0x01u;
    uint32_t push_active = (g_live_p88_iris_audio >> 23) & 0x01u;
    uint32_t target_ire  = (g_live_p88_iris_audio >> 24) & 0x7fu;
    if (target_ire == 0u || target_ire > 109u) target_ire = 41u;

    uint32_t p = page % 25u;
    int is_shooting_page = (p <= 3u || p == 6u || p == 16u || p == 17u);
    int non_default = (sm_total > 0u || ch34_pad20 || push_active || iris_x100 != 280u ||
                       meter != 0u || g_live_p88_user_bits != 0xa0010001u);
    if (!is_shooting_page && !non_default) {
        return;
    }

    static const char * const k_meter_lbl[4] = { "MULTI", "CENTER", "SPOT", "HI-LIGHT" };

    /* Pill 1 (Top-Right below Phase 40 strip): [F2.8 AUTO-IRIS 41%IRE MULTI/HI-LIGHT] */
    int ix = 636, iy = 48, iw = 312, ih = 24;
    uint32_t ibg = push_active ? 0xFF064E3Bu : ((meter == 3u) ? 0xFF422006u : 0xFF0F172Au);
    uint32_t ibd = push_active ? 0xFF22C55Eu : ((meter == 3u) ? 0xFFF59E0Bu : 0xFF38BDF8u);
    fx6_osd_fill_rect(ix, iy, iw, ih, ibg);
    fx6_osd_border_rect(ix, iy, iw, ih, ibd);

    char iris_lbl[56];
    unsigned ip = 0u;
    ip = fx6_append_cstr(iris_lbl, ip, sizeof(iris_lbl), "[F");
    ip = fx6_append_uint(iris_lbl, ip, sizeof(iris_lbl), iris_x100 / 100u);
    ip = fx6_append_cstr(iris_lbl, ip, sizeof(iris_lbl), ".");
    if ((iris_x100 % 10u) == 0u) {
        ip = fx6_append_uint(iris_lbl, ip, sizeof(iris_lbl), (iris_x100 % 100u) / 10u);
    } else {
        ip = fx6_append_2d(iris_lbl, ip, sizeof(iris_lbl), iris_x100 % 100u);
    }
    if (push_active) {
        ip = fx6_append_cstr(iris_lbl, ip, sizeof(iris_lbl), " AUTO-IRIS ");
    } else {
        ip = fx6_append_cstr(iris_lbl, ip, sizeof(iris_lbl), " ");
    }
    ip = fx6_append_uint(iris_lbl, ip, sizeof(iris_lbl), target_ire);
    ip = fx6_append_cstr(iris_lbl, ip, sizeof(iris_lbl), "%IRE ");
    ip = fx6_append_cstr(iris_lbl, ip, sizeof(iris_lbl), k_meter_lbl[meter & 3u]);
    ip = fx6_append_cstr(iris_lbl, ip, sizeof(iris_lbl), "]");
    (void)ip;
    fx6_render_string_text_styled(appfw, ix + 6, iy + 2, iw - 12, 20, iris_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);

    int next_y = iy + 28;

    /* Pill 2: Gold [*M1 / *M2] ShotMark Counter & Latest Mark Pill */
    if (sm_total > 0u) {
        int sx = 636, sy = next_y, sw = 312, sh = 24;
        fx6_osd_fill_rect(sx, sy, sw, sh, 0xFF451A03u);
        fx6_osd_border_rect(sx, sy, sw, sh, 0xFFFBBF24u);
        /* Crisp gold star/diamond mark emblem */
        fx6_osd_fill_rect(sx + 6, sy + 7, 10, 10, 0xFFFBBF24u);
        fx6_osd_fill_rect(sx + 9, sy + 4, 4, 16, 0xFFFDE047u);
        fx6_osd_fill_rect(sx + 3, sy + 10, 16, 4, 0xFFFDE047u);

        char sm_lbl[56];
        unsigned sp = 0u;
        sp = fx6_append_cstr(sm_lbl, sp, sizeof(sm_lbl), "[M1:");
        sp = fx6_append_uint(sm_lbl, sp, sizeof(sm_lbl), sm1_cnt);
        sp = fx6_append_cstr(sm_lbl, sp, sizeof(sm_lbl), " / M2:");
        sp = fx6_append_uint(sm_lbl, sp, sizeof(sm_lbl), sm2_cnt);
        sp = fx6_append_cstr(sm_lbl, sp, sizeof(sm_lbl), "] ");
        sp = fx6_append_cstr(sm_lbl, sp, sizeof(sm_lbl), (last_type == 2u) ? "KEEP@" : "OK@");
        sp = fx6_append_uint(sm_lbl, sp, sizeof(sm_lbl), last_frame);
        (void)sp;
        fx6_render_string_text_styled(appfw, sx + 22, sy + 2, sw - 28, 20, sm_lbl,
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
        next_y += 28;
    }

    /* Pill 3: [CH3/4 -20dB SAFE] + SMPTE 12M User-Bits Pill */
    if (ch34_pad20 || g_live_p88_user_bits != 0xa0010001u) {
        int ax = 636, ay = next_y, aw = 312, ah = 24;
        fx6_osd_fill_rect(ax, ay, aw, ah, ch34_pad20 ? 0xFF064E3Bu : 0xFF0F172Au);
        fx6_osd_border_rect(ax, ay, aw, ah, ch34_pad20 ? 0xFF10B981u : 0xFF38BDF8u);

        char au_lbl[56];
        unsigned ap = 0u;
        if (ch34_pad20) {
            ap = fx6_append_cstr(au_lbl, ap, sizeof(au_lbl), "[CH3/4 -20dB SAFE] UB ");
        } else {
            ap = fx6_append_cstr(au_lbl, ap, sizeof(au_lbl), "[UB ");
        }
        ap = fx6_append_hex8(au_lbl, ap, sizeof(au_lbl), g_live_p88_user_bits);
        if (!ch34_pad20) {
            ap = fx6_append_cstr(au_lbl, ap, sizeof(au_lbl), "]");
        }
        (void)ap;
        fx6_render_string_text_styled(appfw, ax + 6, ay + 2, aw - 12, 20, au_lbl,
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
    }
}

static void fx6_render_phase95_gyroflow_anamorphic_tone_overlay(uint64_t appfw, uint32_t page) {
    if (!g_osd || !(g_live_p95_anamorphic_ibis & 0x80000000u)) return;

    static const char * const k_sq_lbl[6] = {
        "1.00x", "1.30x", "1.33x", "1.50x", "1.80x", "2.00x"
    };
    static const char * const k_ibis_lbl[5] = {
        "OFF", "STD", "ACT", "ASYM", "0x0400"
    };

    uint32_t sq_idx         = g_live_p95_anamorphic_ibis & 0x07u;
    if (sq_idx > 5u) sq_idx = 0u;
    uint32_t eff_ibis_idx   = (g_live_p95_anamorphic_ibis >> 3) & 0x07u;
    if (eff_ibis_idx > 4u) eff_ibis_idx = 1u;
    uint32_t ibis_arb       = (g_live_p95_anamorphic_ibis >> 9) & 0x01u;
    uint32_t center_lock    = (g_live_p95_anamorphic_ibis >> 10) & 0x01u;
    uint32_t yaw_gain_pct   = (g_live_p95_anamorphic_ibis >> 11) & 0xffu;
    if (yaw_gain_pct > 100u) yaw_gain_pct = 100u;

    uint32_t imu_x10        = g_live_p95_gyro_rtmd & 0xfffu;
    if (imu_x10 == 0u) imu_x10 = 834u;
    uint32_t skew_x10       = (g_live_p95_gyro_rtmd >> 12) & 0xffu;
    if (skew_x10 == 0u) skew_x10 = 87u;
    uint32_t rtmd_st_idx    = (g_live_p95_gyro_rtmd >> 20) & 0x03u;
    uint32_t rtmd_susp_sq   = (g_live_p95_gyro_rtmd >> 22) & 0x01u;

    uint32_t tone_req       = g_live_p95_tone_limiter & 0x01u;
    uint32_t tone_eff       = (g_live_p95_tone_limiter >> 1) & 0x01u;
    uint32_t tone_inhib     = (g_live_p95_tone_limiter >> 2) & 0x01u;
    uint32_t bars_eff       = (g_live_p95_tone_limiter >> 3) & 0x01u;
    uint32_t lim_en         = (g_live_p95_tone_limiter >> 4) & 0x01u;
    uint32_t lim_eng        = (g_live_p95_tone_limiter >> 5) & 0x01u;

    uint32_t p = page % 25u;
    int is_shooting_page = (p <= 3u || p == 6u || p == 16u || p == 17u);
    int non_default = (sq_idx > 0u || ibis_arb || center_lock || eff_ibis_idx >= 3u ||
                       rtmd_susp_sq || tone_req || bars_eff || lim_en);
    if (!is_shooting_page && !non_default) {
        return;
    }

    /* 1. Anamorphic De-Squeeze Guide Frame (when squeeze > 1.0x) */
    if (sq_idx > 0u) {
        int gx0 = 20, gx1 = 1003;
        int gy0 = (sq_idx >= 4u) ? 72 : 52;
        int gy1 = (sq_idx >= 4u) ? 418 : 438;
        uint32_t gcol = center_lock ? 0xF59E0Bu : 0x22D3EEu;
        fx6_osd_blend_rect(gx0, gy0, gx1 - gx0 + 1, 2, gcol, 212u);
        fx6_osd_blend_rect(gx0, gy1 - 1, gx1 - gx0 + 1, 2, gcol, 212u);
        fx6_draw_corner_ticks(gx0, gy0, gx1, gy1, 20, 3, gcol, 240u);
    }

    /* 2. Pill 1 (Center-Top y=48): Anamorphic De-Squeeze + IBIS Arbitrator / Yaw-Gain */
    int ax = 322, ay = 48, aw = 304, ah = 24;
    uint32_t abg = center_lock ? 0xFF422006u : (ibis_arb ? 0xFF0E7490u : 0xFF0F172Au);
    uint32_t abd = center_lock ? 0xFFF59E0Bu : (sq_idx > 0u ? 0xFF22D3EEu : 0xFF38BDF8u);
    fx6_osd_fill_rect(ax, ay, aw, ah, abg);
    fx6_osd_border_rect(ax, ay, aw, ah, abd);

    /* Proportional horizontal yaw-gain micro-bar inside Pill 1 */
    int bar_x = ax + 6, bar_y = ay + 18, bar_w = 48;
    fx6_osd_fill_rect(bar_x, bar_y, bar_w, 3, 0xFF1E293Bu);
    int fill_w = (int)((yaw_gain_pct * (uint32_t)bar_w) / 100u);
    if (fill_w < 2 && yaw_gain_pct > 0u) fill_w = 2;
    if (fill_w > bar_w) fill_w = bar_w;
    if (fill_w > 0) {
        fx6_osd_fill_rect(bar_x, bar_y, fill_w, 3, center_lock ? 0xFFF59E0Bu : 0xFF22D3EEu);
    }

    char ibis_lbl[56];
    unsigned ip = 0u;
    ip = fx6_append_cstr(ibis_lbl, ip, sizeof(ibis_lbl), "[DSQ ");
    ip = fx6_append_cstr(ibis_lbl, ip, sizeof(ibis_lbl), k_sq_lbl[sq_idx]);
    ip = fx6_append_cstr(ibis_lbl, ip, sizeof(ibis_lbl), " IBIS:");
    ip = fx6_append_cstr(ibis_lbl, ip, sizeof(ibis_lbl), k_ibis_lbl[eff_ibis_idx]);
    if (center_lock) {
        ip = fx6_append_cstr(ibis_lbl, ip, sizeof(ibis_lbl), " CTR-LCK");
    } else {
        ip = fx6_append_cstr(ibis_lbl, ip, sizeof(ibis_lbl), " YAW=");
        ip = fx6_append_uint(ibis_lbl, ip, sizeof(ibis_lbl), yaw_gain_pct);
        ip = fx6_append_cstr(ibis_lbl, ip, sizeof(ibis_lbl), "%");
    }
    if (ibis_arb) {
        ip = fx6_append_cstr(ibis_lbl, ip, sizeof(ibis_lbl), "*");
    }
    ip = fx6_append_cstr(ibis_lbl, ip, sizeof(ibis_lbl), "]");
    (void)ip;
    fx6_render_string_text_styled(appfw, ax + 6, ay + 1, aw - 12, 18, ibis_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);

    /* 3. Pill 2 (Center y=76): Gyroflow 2000Hz RTMD Readiness & IMX510 Skew */
    int gx = 322, gy = 76, gw = 304, gh = 24;
    uint32_t gbg = rtmd_susp_sq ? 0xFF7F1D1Du : (rtmd_st_idx == 1u ? 0xFF064E3Bu : 0xFF0B192Cu);
    uint32_t gbd = rtmd_susp_sq ? 0xFFEF4444u : (rtmd_st_idx == 1u ? 0xFF10B981u : 0xFF22D3EEu);
    fx6_osd_fill_rect(gx, gy, gw, gh, gbg);
    fx6_osd_border_rect(gx, gy, gw, gh, gbd);

    char gyro_lbl[56];
    unsigned gp = 0u;
    gp = fx6_append_cstr(gyro_lbl, gp, sizeof(gyro_lbl), "[GYRO ");
    gp = fx6_append_uint(gyro_lbl, gp, sizeof(gyro_lbl), imu_x10 / 10u);
    gp = fx6_append_cstr(gyro_lbl, gp, sizeof(gyro_lbl), ".");
    gp = fx6_append_uint(gyro_lbl, gp, sizeof(gyro_lbl), imu_x10 % 10u);
    gp = fx6_append_cstr(gyro_lbl, gp, sizeof(gyro_lbl), "/");
    gp = fx6_append_uint(gyro_lbl, gp, sizeof(gyro_lbl), skew_x10 / 10u);
    gp = fx6_append_cstr(gyro_lbl, gp, sizeof(gyro_lbl), ".");
    gp = fx6_append_uint(gyro_lbl, gp, sizeof(gyro_lbl), skew_x10 % 10u);
    gp = fx6_append_cstr(gyro_lbl, gp, sizeof(gyro_lbl), "ms ");
    if (rtmd_susp_sq) {
        gp = fx6_append_cstr(gyro_lbl, gp, sizeof(gyro_lbl), "SUSP_BY_SQ]");
    } else if (rtmd_st_idx == 1u) {
        gp = fx6_append_cstr(gyro_lbl, gp, sizeof(gyro_lbl), "CTR_LOCKED]");
    } else {
        gp = fx6_append_cstr(gyro_lbl, gp, sizeof(gyro_lbl), "RTMD_READY]");
    }
    (void)gp;
    fx6_render_string_text_styled(appfw, gx + 6, gy + 2, gw - 12, 20, gyro_lbl,
                                  0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);

    /* 4. Pill 3 (Center y=104): 1kHz -20dBFS Reference Tone / SMPTE Color Bars & 4-Ch Limiter */
    if (tone_req || bars_eff || lim_en) {
        int tx = 322, ty = 104, tw = 304, th = 24;
        uint32_t tbg = tone_inhib ? 0xFF451A03u : ((tone_eff || bars_eff) ? 0xFF1E1B4Bu : 0xFF064E3Bu);
        uint32_t tbd = tone_inhib ? 0xFFF59E0Bu : (lim_eng ? 0xFFEF4444u : (tone_eff ? 0xFFA78BFAu : 0xFF10B981u));
        fx6_osd_fill_rect(tx, ty, tw, th, tbg);
        fx6_osd_border_rect(tx, ty, tw, th, tbd);

        if (bars_eff) {
            static const uint32_t k_bars[7] = {
                0xFFE5E7EBu, 0xFFFACC15u, 0xFF22D3EEu, 0xFF22C55Eu, 0xFFD946EFu, 0xFFEF4444u, 0xFF2563EBu
            };
            for (int b = 0; b < 7; b++) {
                fx6_osd_fill_rect(tx + 244 + b * 8, ty + 4, 8, 16, k_bars[b]);
            }
        }

        char tone_lbl[56];
        unsigned tp = 0u;
        if (tone_inhib) {
            tp = fx6_append_cstr(tone_lbl, tp, sizeof(tone_lbl), "[1kHz INHIBITED:REC");
        } else if (tone_eff) {
            tp = fx6_append_cstr(tone_lbl, tp, sizeof(tone_lbl), "[1kHz -20dBFS TONE");
        } else if (bars_eff) {
            tp = fx6_append_cstr(tone_lbl, tp, sizeof(tone_lbl), "[SMPTE BARS");
        } else {
            tp = fx6_append_cstr(tone_lbl, tp, sizeof(tone_lbl), "[AUDIO");
        }
        if (lim_en) {
            tp = fx6_append_cstr(tone_lbl, tp, sizeof(tone_lbl), lim_eng ? " LIM:-3dB!" : " LIM:-3dB");
        }
        tp = fx6_append_cstr(tone_lbl, tp, sizeof(tone_lbl), "]");
        (void)tp;
        int lbl_w = bars_eff ? (tw - 68) : (tw - 12);
        fx6_render_string_text_styled(appfw, tx + 6, ty + 2, lbl_w, 20, tone_lbl,
                                      0x0200600bu, 0x0200600bu, 0x0200a029u, 0u, 1u);
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
                               const uint32_t *cell_vals, uint32_t rec_fmt_idx, uint32_t lang,
                               uint32_t ibis_xlr) {
    uint64_t h = 1469598103934665603ULL;
    h = (h ^ page) * 1099511628211ULL;
    h = (h ^ sel_box) * 1099511628211ULL;
    h = (h ^ menu_cat) * 1099511628211ULL;
    h = (h ^ menu_item) * 1099511628211ULL;
    h = (h ^ menu_depth) * 1099511628211ULL;
    h = (h ^ rec_fmt_idx) * 1099511628211ULL;
    h = (h ^ lang) * 1099511628211ULL;
    h = (h ^ ibis_xlr) * 1099511628211ULL;
    h = (h ^ g_live_lut_meta) * 1099511628211ULL;
    h = (h ^ g_live_audio_packed) * 1099511628211ULL;
    h = (h ^ g_live_p40_flags) * 1099511628211ULL;
    h = (h ^ g_live_p64_flags) * 1099511628211ULL;
    h = (h ^ g_live_p64_shutter_sq) * 1099511628211ULL;
    h = (h ^ g_live_p64_tc) * 1099511628211ULL;
    h = (h ^ g_live_p73_wb_look) * 1099511628211ULL;
    h = (h ^ g_live_p73_media_clip) * 1099511628211ULL;
    h = (h ^ g_live_p73_flags2) * 1099511628211ULL;
    h = (h ^ g_live_p81_touch_af) * 1099511628211ULL;
    h = (h ^ g_live_p81_pdaf_mag_fc) * 1099511628211ULL;
    h = (h ^ g_live_p81_ciz_flags) * 1099511628211ULL;
    h = (h ^ g_live_p88_shotmark) * 1099511628211ULL;
    h = (h ^ g_live_p88_iris_audio) * 1099511628211ULL;
    h = (h ^ g_live_p88_user_bits) * 1099511628211ULL;
    h = (h ^ g_live_p95_anamorphic_ibis) * 1099511628211ULL;
    h = (h ^ g_live_p95_gyro_rtmd) * 1099511628211ULL;
    h = (h ^ g_live_p95_tone_limiter) * 1099511628211ULL;
    for (int i = 0; i < 24 && g_live_lut_name[i]; i++) {
        h = (h ^ (uint64_t)(unsigned char)g_live_lut_name[i]) * 1099511628211ULL;
    }
    for (int i = 0; i < 6; i++) {
        h = (h ^ cell_vals[i]) * 1099511628211ULL;
    }
    return h;
}

#define FX6_NUM_PAGES 25u

static void fx6_render_dispatch(uint64_t appfw, uint32_t page, uint32_t sel_box,
                                uint32_t menu_cat, uint32_t menu_item, uint32_t menu_depth,
                                const uint32_t *cell_vals, uint32_t rec_fmt_idx, uint32_t lang,
                                uint32_t ibis_xlr) {
    fx6_init_syms();
    for (int i = 0; i < 6; i++) g_live_cells[i] = cell_vals ? cell_vals[i] : 0u;
    g_live_cells[3] = 0u; /* P4 ND-Clear Hardware Lock */
    g_live_ibis_xlr = ibis_xlr;
    uint64_t h = fx6_state_hash(page, sel_box, menu_cat, menu_item, menu_depth, g_live_cells, rec_fmt_idx, lang, ibis_xlr);

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
    fx6_render_phase40_hud_strip(appfw, page, cell_vals);
    fx6_render_phase56_assist_overlays(appfw, page);
    fx6_render_phase64_cine_exposure_overlay(appfw, page);
    fx6_render_phase73_wb_look_dualslot_overlay(appfw, page);
    fx6_render_phase81_touchaf_falsecolor_ciz_overlay(appfw, page);
    fx6_render_phase88_shotmark_iris_overlay(appfw, page);
    fx6_render_phase95_gyroflow_anamorphic_tone_overlay(appfw, page);
    if (g_syms.processCommands) g_syms.processCommands(0);

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
            if (c == 3u) {
                /* P4 Hardware Contract: FX3 body has no physical ND wheel -> lock to Clear */
                mb[8 + 3] = 0u;
            } else {
                mb[8 + c] = (mb[8 + c] + 1u) % (uint32_t)g_cell_specs[c].n_vals;
            }
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
                    mb[8 + 4] = (menu_item - 1u) % 6u;
                } else {
                    menu_depth = 2u;
                    menu_item = 0u;
                }
            } else {
                if (menu_cat == 3u) {
                    mb[14] = menu_item % 5u;
                } else {
                    mb[8 + 4] = menu_item % 6u;
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
    case 9: /* DISP: cycle through curated FX6 UI pages 0..23 cleanly (skipping 24=Universal unless explicitly set) */
        page = (page + 1u) % 24u;
        sel_box = (page == 0u) ? 4u : 0u;
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

    fx6_init_syms();
    fx6_gds_install(fb);
    int (*setcwd)(const char *) = (int (*)(const char *))dlsym((void *)-1, "_ZN2ux4core6Kernel23sys_setCurrentDirectoryEPKc");
    int (*setdb)(const char *) = (int (*)(const char *))dlsym((void *)-1, "_ZN2ux6resmgr15ResourceManager11setDatabaseEPKc");
    if (setcwd) setcwd("/usr/share/app/");
    if (setdb) dprintf(2, "FX6_LIVE setdb=%d\n", setdb("global.xdb"));
    if (g_syms.setFontNameWithNamespace) dprintf(2, "FX6_LIVE setns=%d\n", g_syms.setFontNameWithNamespace(5));
    g_cur_lang = 0u;
    if (g_syms.switchBank) { g_syms.switchBank(0, 0); g_syms.switchBank(1, 4); g_syms.switchBank(2, 4); }

    /* Large arenas so repeated interactive page renders never exhaust memory */
    fx6_add_arena(0, 0x200000U, 0x4000000U);
    fx6_add_arena(1, 0x100000U, 0x2000000U);
    fx6_add_arena(2, 0x100000U, 0x1000000U);
    if (!g_icon_slab) g_icon_slab = (uint8_t *)calloc(1, FX6_ICON_SLAB_BYTES);
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
        for (int i = 0; i < 48; i++) mb[i] = 0;
        mb[0] = 0x4658364cu; /* 'FX6L' */
        mb[1] = 1u;          /* cmd_seq */
        mb[2] = 0u;          /* ack_seq */
        mb[3] = 0u;          /* page 0: Big-6 Home */
        mb[4] = 4u;          /* sel_box: Base Look / 3D LUT highlighted */
        mb[5] = 2u;          /* menu_cat: Shooting */
        mb[6] = 0u;          /* menu_item */
        mb[7] = 0u;          /* menu_depth */
        mb[16] = 0u;         /* lang_id: 0=EN */
        mb[17] = 0u;         /* fx3_p10_hwcode telemetry */
        mb[18] = 0u;         /* cinema_p11_state (ibis_idx=0, xlr_idx=0) */
        mb[19] = 0u;         /* lut_tint_meta */
        mb[26] = 0x30303030u;/* audio_db_packed (-12 dB ch1..ch4) */
        mb[27] = 0x303u;     /* phase40_flags: attached=1, +48V=1, bk4=1, valid=1 */
        mb[28] = 0x8003000cu;/* phase64_flags: valid=1, p12=1, p4_nd_absent=1, base800, ei_step=6, angle, stby, tally=on */
        mb[29] = (24u << 20) | 1800u; /* sq_fps=24, shutter_angle=180.0 deg */
        mb[30] = 0u;         /* phase64_tc_frames */
        mb[31] = 0x43494e45u;/* 'CINE' */
        mb[32] = 0xc0c6af02u;/* phase73_wb_look: valid=1, soft_map=1, S-Cinetone, SL=off, tint=0(99), 5600K, preset_5600k */
        mb[33] = 0xa0020020u;/* phase73_media_clip: proxy_eff=1, 16M, simul, clip=1, pos=C, reel=1, cam=A */
        mb[34] = 0u;         /* phase73_flags2 */
        mb[35] = 0x57424c4du;/* 'WBLM' */
        mb[36] = 0x4e50e780u;/* phase81_touch_af: off, (480,270), pdaf=313 */
        mb[37] = 0x64648250u;/* phase81_pdaf_mag_fc: (16,9), mag=1x, fc=off, hdmi=1x, eff=100, req=100 */
        mb[38] = 0x80000004u;/* phase81_ciz_flags: valid=1, spd=4 */
        mb[39] = 0x54414643u;/* 'TAFC' */
        mb[40] = 0u;         /* phase88_shotmark */
        mb[41] = 0xa9040118u;/* phase88_iris_audio: valid=1, ire=41, pad=0, push=0, ae=0, multi, F2.8 */
        mb[42] = 0xa0010001u;/* phase88_user_bits: A0:01:00:01 */
        mb[43] = 0x534d524bu;/* 'SMRK' */
        mb[44] = 0x8f032048u;/* phase95_anamorphic_ibis: valid=1, touch_x=480, yaw=100%, eff=Std, req=Std */
        mb[45] = 0x64857342u;/* phase95_gyro_rtmd: sq=1.0(50), ready=1, skew=8.7ms(87), imu=83.4(834) */
        mb[46] = 0x80507800u;/* phase95_tone_limiter: valid=1, tone=-20dBFS, lim=-3.0dBFS */
        mb[47] = 0x4759524fu;/* 'GYRO' */
    }
    g_live_lut_meta = 0u;
    g_live_lut_name[0] = 0;
    g_live_audio_packed = 0x30303030u;
    g_live_p40_flags = 0x303u;
    g_live_p64_flags = 0x8003000cu;
    g_live_p64_shutter_sq = (24u << 20) | 1800u;
    g_live_p64_tc = 0u;
    g_live_p73_wb_look = 0xc0c6af02u;
    g_live_p73_media_clip = 0xa0020020u;
    g_live_p73_flags2 = 0u;
    g_live_p81_touch_af = 0x4e50e780u;
    g_live_p81_pdaf_mag_fc = 0x64648250u;
    g_live_p81_ciz_flags = 0x80000004u;
    g_live_p88_shotmark = 0u;
    g_live_p88_iris_audio = 0xa9040118u;
    g_live_p88_user_bits = 0xa0010001u;
    g_live_p95_anamorphic_ibis = 0x8f032048u;
    g_live_p95_gyro_rtmd = 0x64857342u;
    g_live_p95_tone_limiter = 0x80507800u;

    /* Pre-warm Page 1 (Three-Layer Menu) and Page 6 (HUD Strip) into guest RAM cache
     * so clicking MENU or DISP in the browser is instantaneous (<25ms)! */
    fx6_render_dispatch(g_appfw, 1u, 4u, 2u, 0u, 0u, cell_vals, 0u, g_cur_lang, 0u);
    fx6_render_dispatch(g_appfw, 6u, 4u, 2u, 0u, 0u, cell_vals, 0u, g_cur_lang, 0u);

    /* Render initial Big-6 Home page */
    fx6_render_dispatch(g_appfw, mb ? mb[3] : 0u, mb ? mb[4] : 4u,
                        mb ? mb[5] : 2u, mb ? mb[6] : 0u, mb ? mb[7] : 0u,
                        cell_vals, mb ? mb[14] : 0u, g_cur_lang, mb ? mb[18] : 0u);
    uint32_t nz = fx6_count_nonzero(g_osd);
    if (mb) {
        mb[15] = ((uint32_t)g_text_ok << 24) | (nz & 0x00ffffffu);
        mb[2]  = mb[1];
    }
    dprintf(2, "FX6_LIVE_READY seq=%u page=%u sel=%u cat=%u item=%u depth=%u nz=%u text_ok=%d fill=%d icon=%d lang=%u p64=0x%08x p73=0x%08x p81=0x%08x p88=0x%08x p95=0x%08x\n",
            mb ? mb[2] : 1u, mb ? mb[3] : 0u, mb ? mb[4] : 4u,
            mb ? mb[5] : 2u, mb ? mb[6] : 0u, mb ? mb[7] : 0u,
            nz, g_text_ok, g_fill_n, g_icon_n, g_cur_lang, g_live_p64_flags, g_live_p73_wb_look, g_live_p81_ciz_flags, g_live_p88_iris_audio, g_live_p95_anamorphic_ibis);
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
            uint32_t req_seq  = mb[1];
            uint32_t page     = mb[3];
            uint32_t sel_box  = mb[4];
            uint32_t cat      = mb[5];
            uint32_t item     = mb[6];
            uint32_t depth    = mb[7];
            uint32_t rec_fmt  = mb[14];
            uint32_t lang     = mb[16];
            uint32_t ibis_xlr = mb[18];
            for (int i = 0; i < 6; i++) cell_vals[i] = mb[8 + i];
            if ((page % FX6_NUM_PAGES) != 24u) {
                cell_vals[3] = 0u; /* P4 ND-Clear Lock */
                mb[8 + 3] = 0u;
            }
            if (mb[27] & 0x200u) {
                g_live_lut_meta     = mb[19];
                fx6_unpack_lut_name(mb, g_live_lut_name, sizeof(g_live_lut_name));
                g_live_audio_packed = mb[26];
                g_live_p40_flags    = mb[27] | 0x100u; /* P12 BK4 Airplane-Mode Shadow Locked */
            }
            if (mb[28] & 0x80000000u) {
                g_live_p64_flags      = mb[28] | 0x00030000u; /* Enforce P4 ND absent & P12 RF-OFF */
                g_live_p64_shutter_sq = mb[29];
                g_live_p64_tc         = mb[30];
            }
            if ((mb[32] & 0x80000000u) && mb[35] == 0x57424c4du) {
                g_live_p73_wb_look    = mb[32] | 0x40000000u; /* FX3 WB switch soft-mapped */
                g_live_p73_media_clip = mb[33];
                g_live_p73_flags2     = mb[34];
            }
            if ((mb[38] & 0x80000000u) && mb[39] == 0x54414643u) {
                g_live_p81_touch_af    = mb[36];
                g_live_p81_pdaf_mag_fc = mb[37] | 0x8000u; /* clean_hdmi_unmagnified = 1 */
                g_live_p81_ciz_flags   = mb[38];
            }
            if ((mb[41] & 0x80000000u) && mb[43] == 0x534d524bu) {
                g_live_p88_shotmark   = mb[40];
                g_live_p88_iris_audio = mb[41];
                g_live_p88_user_bits  = mb[42];
            }
            if ((mb[44] & 0x80000000u) && (mb[46] & 0x80000000u) && mb[47] == 0x4759524fu) {
                g_live_p95_anamorphic_ibis = mb[44];
                g_live_p95_gyro_rtmd       = mb[45];
                g_live_p95_tone_limiter    = mb[46];
            }
            fx6_apply_lang(lang);

            fx6_render_dispatch(g_appfw, page, sel_box, cat, item, depth, cell_vals, rec_fmt, g_cur_lang, ibis_xlr);
            uint32_t cur_nz = fx6_count_nonzero(g_osd);
            mb[15] = ((uint32_t)g_text_ok << 24) | (cur_nz & 0x00ffffffu);
            mb[2]  = req_seq;
            dprintf(2, "FX6_LIVE_FRAME seq=%u page=%u sel=%u cat=%u item=%u depth=%u nz=%u text_ok=%d fill=%d icon=%d lang=%u ibis_xlr=%u lut_meta=0x%08x p40=0x%08x CINE_EXP=0x%08x:0x%08x:%u WB_MEDIA=0x%08x:0x%08x:0x%08x TAFC=0x%08x:0x%08x:0x%08x SMRK=0x%08x:0x%08x:0x%08x GYRO=0x%08x:0x%08x:0x%08x\n",
                    req_seq, page, sel_box, cat, item, depth, cur_nz, g_text_ok, g_fill_n, g_icon_n, g_cur_lang, ibis_xlr, g_live_lut_meta, g_live_p40_flags, g_live_p64_flags, g_live_p64_shutter_sq, g_live_p64_tc, g_live_p73_wb_look, g_live_p73_media_clip, g_live_p73_flags2, g_live_p81_touch_af, g_live_p81_pdaf_mag_fc, g_live_p81_ciz_flags, g_live_p88_shotmark, g_live_p88_iris_audio, g_live_p88_user_bits, g_live_p95_anamorphic_ibis, g_live_p95_gyro_rtmd, g_live_p95_tone_limiter);
        }
    }
}
