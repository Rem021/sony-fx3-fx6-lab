# Wave-27 全球索尼真机情报同步：`ILME-FX3` (`Ver. 7.02`) `[De-Squeeze Display]` (`1.6x=1.65x` 变形宽银幕与四项硬件强锁)、无内置菜单的外置 `M&C Focus Map` (`>=150fps` 截止) 与双卡 `[Simult. + Auto Switch]` / `[Shockless WB]` 真机规则

## 1. 结论先行

基于索尼官方 `ILME-FX3` (`Ver. 7.00 / 7.02`) 及 `Monitor & Control` 帮助指南（`helpguide.sony.net`）核验，确立 **Wave-27 三项真机状态机与移植护栏**：

1. **`[De-Squeeze Display]` 五档精确倍率（`1.6x` 实为 `1.65` 倍校正）、四项相机强锁与五类 HDMI/模式旁路**：
   - 菜单枚举（`MENU -> Setup -> [Display Option] -> [De-Squeeze Display]`）：`Off`、`1.3x`、`2.0x` 及 `Ver. 7.00+` 新增的 **`1.5x`** 与 **`1.6x`（实际执行 `1.65` 倍水平拉伸还原 `2.39:1` CinemaScope）**。
   - **开启非 `Off` 时的四项底层强锁**：`[Focus Mode]` 锁死 `Manual Focus`、`[Focus Area]` 锁死 `Wide`、`[SteadyShot]` 锁死 `Off`（禁 IBIS 防畸变撕裂）、`[Face Priority in Multi Metering]` 锁死 `Off`。
   - **自动抑制反挤压条件**：`[HDMI Output Settings] -> [RAW Output] = [On]`、`[Rec. Media dur HDMI Output] = [Off(HDMI Only)]`（同时强制关闭 `[HDMI Info. Display]`）、`[Log Shooting] = [Off]`、`[Remote Shooting]` 监看及照片模式。
2. **`ILME-FX3` 无机内 `[Focus Map]` 菜单（对比 `FX30`）与外置 `Monitor & Control` `>=150fps` 截止边界**：
   - 真机 `ILME-FX3`（含 `Ver. 7.02`）**机内菜单无内置 `[Focus Map]` 开关**，其焦点图（`Ver. 6.00+`）仅向外部 `Monitor & Control` App 输出相位对焦深度流。
   - **硬禁用条件**：帧率 **`>= 150 fps`**（如 `S&Q` `200fps / 240fps`，注：`<=6fps` 下限仅适用于 `ILME-FX6`）、无镜头/转接环/非相位检测镜头、机内回放态。Stage-B 切勿在 `FX3` 机内强刷不存在的本地硬件 Focus Map 叠加层。
3. **双卡 `[Simult. Recording]` + `[Auto Switch Media]` (`Ver. 2.0+` 单卡续录 vs `Off` 严格双备份) 与 `[Shockless WB]` 即时旁路规则**：
   - `Ver. 2.0..7.02` 下，`[Simult. Recording]` 配合 `[Auto Switch Media] = [On]` 时，任一卡满后**自动降级在剩余单卡继续录制**（换入空卡即恢复双卡同录）；若需强制双份冗余缺一不可，必须设 `[Auto Switch Media] = [Off]`（对比冷备双卡金库规则）。
   - `[Shockless WB]`（`Off / 1 (Fast) / 2 / 3 (Slow)`）全帧率可用（含 `100p/120p` 与 `200/240fps S&Q`），平滑预设切换；但 **`[C.Temp./Filter]` 直接改色温 K 值与 `A–B / G–M` 微调网格绕过平滑、立即生效**。

## 2. 工程映射

- **`outputs/fx6-native-presenter-closure/`（Round 41）**：在真实 `FX3 7.02` (`4.9.337-scel+`) ARM64 QEMU 实测 `1.6x(1.65x)` 四项强锁与 HDMI RAW 旁路、外置 `Focus Map >=150fps` 截止及双卡续录/`Shockless WB` K 值即时旁路 + `16/16 H0 == H3`。
- **`outputs/fx3-firmware-lab/` · `outputs/fx3-safety/` · `outputs/fx3-recovery-adapter/` · `outputs/fx3-vm/`**：待 Wave-26 完结后顺次推进 Wave-27 全栈验证。
