# Wave-25 全球索尼真机情报同步：`ILME-FX3` (`Ver. 7.02`) 散热风扇四态 PWM（无 `Auto1/Auto2`）、快门角度 (`5.6°..64F / 360°`) 独立存储与 `Ver. 6.01 -> 7.00/7.02` 机内 User LUT 二进制槽位格式代际分裂

## 1. 结论先行

基于索尼官方 `ILME-FX3` (`Ver. 7.00 / 7.02`) 帮助指南与固件更新说明，提炼 **Wave-25 三项关键物理真机边界**：

1. **`ILME-FX3` 机内主动散热风扇 `[Fan Control]` 精确四态枚举与热保护红线**：
   - 真机菜单路径 `MENU -> Setup -> [Setup Option] -> [Fan Control]` 严格仅含四项：**`Auto`**、**`Minimum`**、**`Off in Rec`**、**`Always Off`**（注：`Auto1`/`Auto2` 属于演播室摄像机或松下 Lumix，在 `ILME-FX3` 上并不存在！）。
   - **`Off in Rec` 物理行为**：录制期间停转风扇（除非内部温度越过紧急安全阈值），而在**待机/非录制期间以最高转速 (`MAX PWM`) 全速排热**。
   - **冷备份与固件预演护栏**：若用户在 Stock FX3 中停留在 `Always Off`，在执行长耗时 `AdjustControl (0x40)` 75 MiB `p3` 冷备份或高负载双系统测试前，预检器必须提示/强制风扇处于 `Auto`（并识别 `[Auto Power OFF Temp.] = Standard / High`），严防 `CXD90057 / CXD90058` 过热断电。
2. **`[Shutter Mode]` (`Speed` vs `Angle`) 独立键值存储与角度量程边界**：
   - 自 `Ver. 6.00+`（含 `7.00 / 7.02` 及 `BIG6` 主界面）支持 `Speed` 与 `Angle`：常规录制量程为 **`5.6° .. 64F`**（当 `[Rec Frame Rate] = 119.88p / 100p` 时收敛为 **`5.6° .. 360°`**），`S&Q` 模式量程为 **`5.6° .. 360°`**。
   - 机内 `Backup.bin` 对 `[Speed]` 与 `[Angle]` 采取**独立槽位存储**，且不受 `[Exposure step]` (`0.3EV / 0.5EV`) 影响。
3. **`Ver. 6.01` vs `Ver. 7.00 / 7.02` 机内 `p2:/setting` User LUT 编译槽位二进制格式代际不兼容（核心防砖发现！）**：
   - 索尼官方 `Ver. 7.00 / 7.02` 发行说明明确指出：*“优化了用户 LUT 处理（从 Ver. 6.01 或更早版本升级且已注册用户 LUT 的用户，建议重新注册用户 LUT）”*。
   - **真机二进制机理**：我们移植运行的 donor `FX6 Ver. 6.01` (`appFw.so`) 属于 **`<= 6.01` 代际 LUT 序列化格式**，而宿主真机 `Stock FX3 Ver. 7.02` 属于 **`7.00+` 优化后 LUT 序列化格式**。若允许 Stage-B `FX6 6.01` 直接写入真机 `p2:/setting` 的 `User1..User16` LUT 槽位，切回 Stock FX3 `7.02` 时将引发 LUT 色彩解算异常甚至设置加载失败！
   - **硬隔离闭环**：彻底印证将 Stage-B LUT 注册表重定向至内存态 `/tmp/fx6_lut_overlay`、严禁触碰真机 `p2:/setting`（保持 `H0 == H3`）的必要性。
