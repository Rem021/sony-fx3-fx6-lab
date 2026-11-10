# Exact Verified Layout of `ux::core::RawImageDataGRM` + `BMP_Handle` (Verified on Candidate 644 `runs/cp-bind-58120810/serial.log`)

## 1. Why `pix` (`sys_getImageData(image)`) only showed the top rows in Candidate 644 (`0x0000..0x6000`)
In Candidate 644 (`runs/cp-bind-58120810`):
- `raw = sys_getImageData(image) = 0x7f900f12f0` (`ux::core::RawImageDataGRM*`, 56 bytes):
  - `+0x00`: `uint16_t width = 149` (`0x0095`)
  - `+0x02`: `uint16_t height = 38` (`0x0026`)
  - `+0x04`: `uint32_t pitch_px = 160` (`0x000000a0`)
  - `+0x08`: `uint32_t vpitch = 38` (`0x00000026`)
  - `+0x0c`: `uint32_t pf = 7` (`RGBA4444`, 2 bytes per pixel)
  - `+0x18`: `void *bmp = 0x7f900f1570` (`BMP_Handle*`, which is at `raw + 0x280`)
- At `bmp = 0x7f900f1570` (`raw + 0x280` in `FX6_VSR644 0280`):
  - `+0x00`: `0x7f9dbd3a48` (vtable in `libgrm_bmp.so`)
  - `+0x08`: `0x7f900f1330` (inner BMP header at `raw + 0x40`, magic `0x00abcdef`)
  - **`+0x10`: `void *bits = 0x7f900f6270`** (the ACTUAL composited bitmap buffer, which happened to be at `raw + 0x4f80` because individual FreeType glyph cache nodes were allocated at `raw + 0x00c0 .. raw + 0x4f7f`!)

## 2. Exact Row Stride and Pixel Format inside `bits = *(void**)((char*)bmp + 0x10)`
In `FX6_VSR644`, `bits` (`0x7f900f6270`) starts at `raw + 0x4f80`:
- Rows `y = 0, 1, 2` (`0x4f80 .. 0x56ff`, `3 * 640 = 1920 = 0x780` bytes) are transparent top padding (`0`).
- Row `y = 3` (`0x5700`): `........+#######+.........####...` (top arch of `'S'` at cols 8..16, ascender of `'h'` at cols 26..29)
- Row `y = 4` (`0x5980 = 0x5700 + 640`): `......+###########........####...`
- Row `y = 5` (`0x5c00 = 0x5980 + 640`): `.....##############.......####...`
- Row `y = 6` (`0x5e80 = 0x5c00 + 640`): `....######+..++#####......####.............................................................++.......` (arch of `'S'`, stem of `'h'`, top of `'i'`)

Why did `FX6_VSR644` cut off after row 6? Because `FX6_VSR644` dumped `0x6000` bytes starting from `raw` (`0x7f900f12f0`), and `0x4f80 + 6.6 * 640 = 0x6000`!
When you read from **`bits = *(void**)((char*)bmp + 0x10)`** directly, all `38` rows (`38 * 640 = 24,320` bytes) are present!

## 3. Drop-In C Code to Blit Un-Sheared Native `view_string` `ImageData` into `gpe0` (`0x41e001000`)

```c
static void fx6_blit_imagedata_to_osd(void *image, uint32_t *osd_fb, int dst_x, int dst_y)
{
    void *(*gd)(void*) = (void*(*)(void*))dlsym((void*)-1, "_ZN5libra9ImageData16sys_getImageDataEv");
    if (!gd || !image || !osd_fb) return;
    uint8_t *raw = (uint8_t*)gd(image);
    if (!raw) return;

    int w = *(uint16_t*)(raw + 0x00);
    int h = *(uint16_t*)(raw + 0x02);
    int pitch_px = (int)(*(uint32_t*)(raw + 0x04)); /* 160 */
    uint32_t pf = *(uint32_t*)(raw + 0x0c);         /* 7 = RGBA4444 */
    void *bmp = *(void**)(raw + 0x18);
    if (!bmp || w <= 0 || h <= 0 || pitch_px <= 0) return;

    const uint8_t *bits = *(const uint8_t**)((uint8_t*)bmp + 0x10);
    if (!bits) return;

    int row_stride_bytes = pitch_px * 4; /* 160 * 4 = 640 bytes (0x280) per row */
    for (int y = 0; y < h; y++) {
        if (dst_y + y < 0 || dst_y + y >= 540) continue;
        const uint16_t *src_row = (const uint16_t*)(bits + y * row_stride_bytes);
        uint32_t *dst_row = osd_fb + (dst_y + y) * 960;
        for (int x = 0; x < w; x++) {
            if (dst_x + x < 0 || dst_x + x >= 960) continue;
            uint16_t p = src_row[x];
            uint32_t r = ((p >> 12) & 0xf) * 17;
            uint32_t g = ((p >>  8) & 0xf) * 17;
            uint32_t b = ((p >>  4) & 0xf) * 17;
            uint32_t a = ((p >>  0) & 0xf) * 17;
            if (a != 0) {
                dst_row[dst_x + x] = (a << 24) | (r << 16) | (g << 8) | b;
            }
        }
    }
}
```
