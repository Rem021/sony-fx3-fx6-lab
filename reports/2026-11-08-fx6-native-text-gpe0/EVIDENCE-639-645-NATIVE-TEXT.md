# EVIDENCE 639–645：原生 `view_string` 真实字形首次落入 gpe0

时间：2026-11-08（America/Los_Angeles）
结论：**appFw 自己的 `view_string::onDrawNotice` → `MultiLineTextSprite` → `TextSprite::drawTextImpl`
→ `refreshTextImpl` → `createTextProcessor` → `setImageLoadCallback` 链路已跑通**，
libra/uxengine 用真实字库栅格化出的位图被写入 `0x41e001000`（gpe0），字形可读（`Shooting`）。

全程没有手写任何坐标拼 UI：唯一的绘制调用是 appFw 的 `onDrawNotice`，像素来自 libra 生成的 `ImageData`。

## 1. 候选与运行

| 候选 | CPIO | run | 关键结果 |
|---|---|---|---|
| 639 | `guest-hybrid-fx6kernel-capid-grmreal639-vsdrawn.cpio` | `cp-bind-9de6252e` | 5 点修复后 onDrawNotice 正常返回，但 drawTextImpl 早退 |
| 640 | `...grmreal640-textflags.cpio` | `cp-bind-271ef90e` | `validText=1`、callback 首次触发，拿到 `ImageData` |
| 641 | `...grmreal641-textpix.cpio` | `cp-bind-0751f30a` | 首次落盘 1002 px，但字形被横向拉糊 |
| 642 | 复用 641 CPIO（仅改捕获时序） | `cp-bind-c68dcad4` | `gpe0-final.bin` nz=3614，确认落盘非捕获问题 |
| 643 | `...grmreal643-pixdump.cpio` | `cp-bind-b82adf59` | 逐 stride 抽样，发现缓冲有头部结构 |
| 644 | `...grmreal644-hexdump.cpio` | `cp-bind-58120810` | 24 KB hex dump，解出 `RawImageDataGRM` 精确布局 |
| 645 | `...grmreal645-rgba4444.cpio` | `cp-bind-912b30d1` | **正确 blit：copied=1522 opaque=931，字形清晰** |

## 2. 645 串口证据（关键 4 行）

```
FX6_VSR645 raw=0x7f7c0f5b60 w=149 h=38 pitch=160 pf=7 bmp=0x7f7c0f12f0
FX6_VSR645 bits=0x7f7c0f6270
FX6_VSR645 blit copied=1522 opaque=931 at 40,80
FX6_OSD_SCAN 41e nz_words=1522
```

`gpe0-final.bin`：非零像素 1522，包围盒 x∈[42,186]、y∈[83,115]，
主色 `0xffff00ff`（opaque white/magenta-ish OSD word），与 native 位图 149×38 对齐。

## 3. 关键修复（639 → 645）

1. **控件几何**：`vs+0x1e8/+0x1ec/+0x1f0/+0x1f4` 必须非零，否则 `0xc3c348` 调 `TextSprite::setClipSize(0,0)`。
2. **ResID**：`+0x208 = 0x02006001`（行高 36，绕过未初始化的 `0x42d5798` 哈希表），`+0x210 = 0x0200a029`（左对齐）。
3. **TextSprite 标志**：`*(u16*)(ts+0xa8)`：
   - bit3 `0x0008` → `drawText()` 才会 tail-call `drawTextImpl`；
   - **bit1|bit2 `0x0006`** → `drawTextImpl(0x80260)` 自身才不会在 `0x80270` 处直接 `ret 1`。
   两个条件都必须满足。
4. **资源**：`addArena(0/1/2)` + `sys_loadFontData` 覆盖 `0x0200a005..a00a`、`0x02006000..6005`、`0x02008000..8002`（15/15 rc=1）。
5. **图像回调**：`setImageLoadCallback` 必须安装，否则 `onSetTextImage` 拿到图像后直接丢弃。
6. **位图取址（最关键）**：`ImageData::sys_getImageData()` 返回的是 `ux::core::RawImageDataGRM`，**不是**像素：
   ```
   +0x00 u16 width=149
   +0x02 u16 height=38
   +0x04 u32 pitch_px=160
   +0x0c u32 pf=7  (RGBA4444)
   +0x18 BMP_Handle* bmp
   bmp+0x10 -> const uint8_t *bits   ← 真正的整行合成位图
   ```
   行步幅 = `pitch_px * 4 = 640` 字节，每像素 `uint16_t` RGBA4444（前 149 个）。
   之前按 `w*4` 线性读，既错位又读到 FreeType 单字缓存节点，才导致横向拉糊。

## 4. 交付物

- `gpe0-645-native-text-crop.png` — 从 645 `gpe0-final.bin` 裁切导出，可见 `Shooting` 为真实字库字形。
- `native-image-644-decoded.png` / `native-alpha-644.png` — 644 错误解码对照（说明为什么需要 `bmp+0x10`）。
- `RAW-IMAGEDATA-GRM-BITS-EXACT.md` — 布局参考。

## 5. 尚未完成

gpe0 目前只有**一行原生文字**，还不是完整菜单界面。下一步需要驱动 appFw 自己的
`procam_big6_menu_home_presenter` / `procam_big6_menu_setting_presenter` +
真实 `view_menu_item` / `view_list_scroll_cursor_fixed` 构建整棵菜单树，
由 presenter 的 `onDrawNotice` 发出多条文字/框线/列表项，仍然禁止手写坐标。
