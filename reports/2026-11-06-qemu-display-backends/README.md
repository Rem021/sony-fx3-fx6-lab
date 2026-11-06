# QEMU 显示后端与 FX3 可见帧路线评估

日期：2026-11-06  
范围：固定 FX3 QEMU 虚拟机的显示后端/抓帧方案，只读研究  
状态：**未启动现有 FX3 VM；未解包/修改固件；未改平台策略；未重建 QEMU**

## 1. 结论摘要

1. 当前 `qemu-gpio5`（QEMU 11.1.2）是**headless-only 构建**：`-display help` 只列出 `none`；`CONFIG_COCOA/SDL/GTK/VNC/SPICE/DBUS_DISPLAY/OPENGL` 全部 `#undef`；`-vnc`、`-spice` 直接报 `invalid option`。
2. 构建里**编译了图形设备**：`bochs-display`、`virtio-gpu-pci`、`ramfb`、`VGA`、`ati-vga`、`cirrus-vga`、`secondary-vga`。但当前命令 `-nodefaults` 且没有 `-vga`/`-device`，所以 guest 里**没有显示设备**；DTB 也没有 `display`/`framebuffer`/`gpu` 节点，内核字符串只有 `simple-framebuffer`，没有 `bochs-drm`/`virtio-gpu`。即使加设备，guest 也没有现成驱动。
3. QMP `screendump` 必须找到 `QemuConsole` 且有 `DisplaySurface`；`-display none` + 无显示设备时没有 console，会报 `There is no console to take a screendump from`。加 `bochs-display` 后也只能抓该设备的 surface，抓不到 Sony LDEC/OSD 的帧。
4. **真正可行的可见帧路线已经存在**：`-display none` + QMP `pmemsave` 读取 guest 物理内存 `0x41e000000` 的 **OSD/GPE ring**，再由 `osd_ring85.py` 转 PNG。已有 `ap103v4ldec600-71ce5752-final-committed.png`（640×480）为证，画面是 FX3 UI（`Principal / 59.94p / ISO 100 / AWB / PP11 / XAVC S HD 50M 420 8bit / MENU`）。
5. 因此：**QEMU 显示后端不是当前最短路径**。对 FX6 也一样，真正缺的是 FX6 appFw/GPE/OSD 发布到 ring 的内容，而不是 QEMU 窗口。Cocoa/SDL 重建只能作为“需要宿主窗口”时的备选，不能替代 guest 侧显示内容。

## 2. 当前 QEMU 构建与命令

### 2.1 构建

- 二进制：`qemu-gpio5-bf4d46481998b8fb`
- 版本：`QEMU emulator version 11.1.2`
- configure：

```text
--target-list=aarch64-softmmu
--without-default-features
--enable-tcg
--enable-fdt
--enable-pixman
--disable-docs
--disable-tools
--disable-guest-agent
--disable-werror
```

`--without-default-features` 是关键：它把 Cocoa/SDL/GTK/VNC/SPICE/DBus/OpenGL 全部关掉，只保留 Pixman。

### 2.2 当前命令

```text
-machine virt,gic-version=2,secure=off
-accel tcg,thread=multi
-cpu cortex-a35
-smp 4
-m 5120
-display none
-nodefaults
-nic none
-no-reboot
-monitor none
-serial file:...
-qmp unix:q,server=on,wait=off
-chardev socket,path=g,server=on,wait=off,id=keygate93
-gdb chardev:keygate93
-S
-kernel .../vmlinux.bin
-device loader,file=...cpio,addr=0x440000000,force-raw=on
-device loader,file=...guest.dtb,addr=0x400002000,force-raw=on
```

注意：

- `-nodefaults` 禁用了默认 VGA；
- 没有 `-vga`、没有 `-device bochs-display`/`virtio-gpu-pci`/`ramfb`；
- 因此 guest 里没有 QEMU 显示设备，只有 Sony 的 LDEC/OSD 路径。

## 3. QEMU 显示后端选项对比

| 后端 | 当前构建 | 作用 | 对 FX3 兼容性 | 能否抓 guest 帧 |
|---|---|---|---|---|
| `none` | **唯一可用** | 不显示视频输出 | 当前用法 | 本身不抓帧；需另用 `pmemsave` |
| `cocoa` | 未编译 (`CONFIG_COCOA` undef) | macOS 原生窗口 | 可用，但需重建 | 只有 guest 驱动了 QEMU 显示设备才有 surface |
| `sdl` | 未编译 (`CONFIG_SDL` undef) | SDL 窗口 | 可用，但需重建/依赖 | 同上 |
| `gtk` | 未编译 (`CONFIG_GTK` undef) | GTK 窗口 | 可用，但依赖重 | 同上 |
| `vnc` | 未编译 (`CONFIG_VNC` undef) | 远程 VNC | 需重建 | 仍需 console + surface |
| `spice` | 未编译 (`CONFIG_SPICE` undef) | SPICE 远程桌面 | 需重建 | 仍需 console + surface |
| `dbus` | 未编译 (`CONFIG_DBUS_DISPLAY` undef) | D-Bus 显示 | 需重建 | 仍需 console + surface |
| `egl-headless` | 未编译 (`CONFIG_OPENGL` undef) | 无窗口 OpenGL | 需重建，且需 VNC/SPICE | 不宜作为本机首选 |
| `curses` | 未在 `-display help` 出现 | 文本终端 | 只适合文本模式 | 不适合图形 UI |

`-display help` 实际输出：

```text
Available display backend types:
none
```

`-vnc help` / `-spice help` 实际输出：

```text
qemu-gpio5-...: -vnc: invalid option
qemu-gpio5-...: -spice: invalid option
```

## 4. 图形设备对比

`-device help` 的 Display devices 段包含：

```text
ati-vga
bochs-display
cirrus-vga
ramfb
secondary-vga
VGA
virtio-gpu-device
virtio-gpu-pci
```

| 设备 | 总线 | 需要 guest 驱动 | 当前 FX3 guest |
|---|---|---|---|
| `bochs-display` | PCI | `bochs-drm` 或 VGA/fb | DTB 无节点；内核未见 `bochs-drm` |
| `virtio-gpu-pci` | PCI | `virtio-gpu`/DRM | 内核未见 `virtio-gpu` |
| `ramfb` | System | `ramfb`/`simple-framebuffer` | DTB 无 `simple-framebuffer` 节点 |
| `VGA`/`cirrus-vga`/`ati-vga` | PCI | 传统 VGA/fb | 当前无 `-vga`，内核未见对应 DRM |

`virtio_mmio` 节点在 DTB 中存在（`virtio_mmio@a000000` 等），但当前命令没有 `virtio-gpu-device`；即使加上，guest 内核也需要 `virtio-gpu` 驱动。

## 5. 为什么 `screendump` 不能直接解决

QEMU `qmp_screendump` 的实现：

```c
if (device) {
    con = qemu_console_lookup_by_device_name(device, has_head ? head : 0, errp);
} else {
    con = qemu_console_lookup_by_index(0);
    if (!con) {
        error_setg(errp, "There is no console to take a screendump from");
        return;
    }
}
surface = qemu_console_surface(con);
if (!surface) {
    error_setg(errp, "no surface");
    return;
}
```

因此：

- `-display none` + 无显示设备 → 没有 console → `screendump` 失败；
- 加 `bochs-display`/`virtio-gpu-pci` → 有 console/surface，但那是该设备的 VGA/GPU framebuffer，不是 Sony LDEC/OSD 帧；
- guest 没有驱动 → surface 可能是黑屏/未初始化；
- `screendump` 不能读取 guest 物理内存里的 OSD ring。

## 6. 已被证明的 headless 抓帧路线

### 6.1 OSD ring

`fx3-osd-headless` 在 guest 内把 OSD 像素发布到预留物理内存：

```text
BASE   = 0x41e000000
TOTAL  = 0xc10000
HEADER = 0x10000
STRIDE = 0x180000
MAGIC  = 0x31474e495244534f  ("OSDRING1")
SLOTS  = 8
```

- 每个 slot 头 21 个 64-bit 字；
- 像素数据从 `slot + 0x100` 开始；
- `fmt=0` 为 16-bit（LUT 展开到 RGBA），`fmt=1` 为 32-bit BGRA→RGBA；
- `osd_ring85.py` 通过 QMP `human-monitor-command` 执行：
  ```text
  pmemsave 0x41e000000 0x100 ...
  pmemsave 0x41e000000 0xc10000 ...
  ```
- 校验 magic、seq、slot 头、`span`、`width/height/stride`、FNV64 后写 PNG；
- 这是 **QMP 只读**，不写 guest，不依赖 QEMU display backend。

### 6.2 已有 PNG 证据

```text
ap103v4ldec600-71ce5752-final-committed.png
640 x 480, RGBA
sha256 e22281813acd1cd28fbfd94bf35ac9ebae0947dbc63394455a5a234114e8ec35
ring_sequence 17
FNV_verified true
```

画面文字：

```text
Principal
59.94p
ISO 100
AWB
PP11
XAVC S HD
50M 420 8bit
Assist OFF
Px OFF
MENU
Fechar
```

这是**既有 FX3 UI 帧**，证明 OSD ring + `pmemsave` 路径能产出真实可见画面。它**不是 FX6 菜单证据**；FX6 的 appFw 目前还没有把 FX6 UI 发布到同一 ring。

### 6.3 LDEC103 路径

串口里有：

```text
FX3_LDEC103_OPEN count=1 devno=0xfb000cd result=0 synthetic_ldec=1 original_ldec_hw=0
FX3_LDEC103_GUEST_EXACT sample=panel-02-1228 compressed=20496 output=491520 result=0 byte_equal=1 output_fnv=0x1936cce630053f25 guard_equal=1
```

这是 **Sony LDEC103 面板解码测试**（`panel-02-1228`），输出 491,520 字节；它是显示链路的另一条证据，但不是 QEMU display backend，也不是 FX6 UI。

## 7. 方案排序

### P0：继续用 OSD/GPE ring + QMP `pmemsave`（推荐）

- 不重建 QEMU；
- 不改平台；
- 不新增显示设备；
- 已有 FX3 640×480 UI 帧证据；
- 对 FX6 只需确认 FX6 appFw 是否发布到同一 OSD ring/GPE；若没有，需找 FX6 的 OSD 发布点。

### P1：重建 QEMU + Cocoa（仅在需要宿主窗口时）

- 在 QEMU 11.1.2 上增加 `--enable-cocoa`（macOS 原生）或 `--enable-sdl`；
- 保留 `--enable-pixman`、`--enable-tcg`、`--enable-fdt`；
- 添加 `-display cocoa`（或 `sdl`）；
- 仍需 `-device bochs-display`/`virtio-gpu-pci` 和 guest 驱动；
- 风险：改变工具链/平台、可能影响时序；需要用户批准。

### P2：VNC/SPICE

- 当前未编译；`-vnc`/`-spice` 无效；
- 重建后可用远程 viewer，但仍需 console + surface；
- 对单机本地调试而言，比 Cocoa 更绕。

### P3：`screendump`

- 当前无 console，直接失败；
- 加显示设备后只能抓该设备的 surface；
- 不能替代 OSD ring。

## 8. 验证步骤（待用户批准，不现在执行）

### A. 复用 OSD ring（无平台改动）

1. 用现有 `FX3_OSD_HEADLESS=software-ring-v1` + `fx3-osd-headless` helper 启动候选；
2. QMP 读取 `0x41e000000` 的 0x100 头和 0xc10000 ring；
3. 用 `osd_ring85.py` 解析，检查 `MAGIC`、slot 头、`width/height/stride/span`、FNV；
4. 输出 PNG，检查 `first_nonuniform_found` 与画面文字；
5. 对 FX6：确认 appFw 是否把像素发布到同一 ring；如果没有，定位 FX6 OSD/GPE 发布点。

### B. QEMU Cocoa 窗口（如确需窗口）

1. 复制 QEMU 源码到独立构建目录，`--enable-cocoa`、`--enable-pixman`、`--enable-tcg`、`--enable-fdt`；
2. 保持 `-machine virt,gic-version=2,secure=off`、`-cpu cortex-a35`、`-smp 4`、`-m 5120`、kernel/DTB/CPIO 不变；
3. 加 `-display cocoa`，加 `-device bochs-display`（或 `virtio-gpu-pci`）；
4. guest 内检查 `/dev/fb0`、`/sys/class/drm`、`dmesg | grep -i bochs/virtio`；
5. QMP `screendump` 带 `device`/`head`，输出 PNG；
6. 若 guest 无驱动，窗口只会黑屏；此时回到 A。

### C. 不建议

- `-display none` + `screendump`（无 console）；
- 只加 `-vnc`/`-spice`（当前构建不支持）；
- 用 `bochs-display` 替代 OSD ring（guest 未驱动）。

## 9. 仍缺的信息

1. FX6 appFw 是否使用与 FX3 相同的 OSD ring/GPE 发布路径；目前没有 FX6 帧。
2. FX6 的 OSD 协议/队列是否与 `fx3-osd-headless` 的 `0x74d/0x84d/0x84e` 一致。
3. macOS 上重建 Cocoa QEMU 的依赖/签名/权限（辅助功能、窗口捕获）是否可用；未验证。
4. 添加 `bochs-display`/`virtio-gpu-pci` 是否会改变 guest PCI 枚举、DTB/时序；未验证。
5. `ap103v4` PNG 的原始 run 是否仍可复现；当前只读确认 PNG 和 JSON，未重跑。
6. 640×480 是 OSD 帧尺寸，不等于最终面板/输出尺寸；仅作为可见 UI 证据。

## 10. 证据与来源

### 10.1 本机只读证据

- QEMU 二进制：`.../qemu-display-build/bin/qemu-gpio5-bf4d46481998b8fb`
- `-display help` 仅 `none`；`-vnc`/`-spice` invalid
- `build/config-host.h`：`CONFIG_COCOA/SDL/GTK/VNC/SPICE/DBUS_DISPLAY/OPENGL` 全部 `#undef`
- `configure-command.json`：`--without-default-features`
- `-device help`：`bochs-display`、`virtio-gpu-pci`、`ramfb`、`VGA` 等
- DTB strings：无 `display`/`framebuffer`/`gpu`/`simple-framebuffer` 节点；有 `virtio_mmio`
- kernel strings：只有 `simple-framebuffer`；无 `bochs-drm`/`virtio-gpu`
- serial：`dmmap_init`、`FX3_LDEC103_*`；无 `drm`/`fb0`/`bochs`/`virtio-gpu`
- `osd_ring85.py`：`pmemsave` + ring 解析 + PNG
- `fx3-osd-headless-v5.c`：OSD ring 发布
- `ap103v4ldec600-71ce5752-final-committed.png` / `.json`

### 10.2 公开/官方来源

- QEMU `qemu-options.hx`（`-display`/`-vnc`/`-spice` 定义）：
  [GitLab raw](https://gitlab.com/qemu-project/qemu/-/raw/master/qemu-options.hx)
- QEMU `ui/console.c`（`qemu_display_init`、默认后端优先级）：
  [GitLab](https://gitlab.com/qemu-project/qemu/-/blob/master/ui/console.c)
- QEMU `ui/ui-qmp-cmds.c`（`qmp_screendump` 需要 console/surface）：
  [GitLab](https://gitlab.com/qemu-project/qemu/-/blob/master/ui/ui-qmp-cmds.c)
- QEMU `qapi/machine.json`（`pmemsave` 命令）：
  [GitLab raw](https://gitlab.com/qemu-project/qemu/-/raw/master/qapi/machine.json)
- QEMU `hw/display/bochs-display.c`：
  [GitLab](https://gitlab.com/qemu-project/qemu/-/blob/master/hw/display/bochs-display.c)
- QEMU `hw/display/virtio-gpu-pci.c`：
  [GitLab](https://gitlab.com/qemu-project/qemu/-/blob/master/hw/display/virtio-gpu-pci.c)
- QEMU 官方 `docs/master/system/display.html` 当前返回 404；本文以 QEMU 11.1.2 源码为准。
- QEMU-devel `screendump` 迁移补丁（社区一手）：
  [lore.kernel.org](https://lore.kernel.org/qemu-devel/20230904115251.4161397-4-marcandre.lureau@redhat.com/)

## 11. 边界与事故说明

- 未启动现有 FX3 VM；未运行任何 guest。
- 未解包/修改 `BODYDATA.DAT` 或任何固件。
- 未重建 QEMU；未修改 `-display`/`-device`/平台参数。
- 未触碰用户待决策的三问（FX6 运行时库 / FDAT 解包 / 平台策略）。
- 核查中曾执行 `-display none -S -machine none` 的显示探针，QEMU 以 `-machine none -S` 挂起；**未加载任何 guest、未读取固件**，随后已 kill，`ps` 确认无残留 QEMU。该探针不作为 VM 运行证据。
- 既有 `ap103v4` PNG 是 FX3 UI，不是 FX6 菜单；不能据此宣称 FX6 开机通过。

## 12. 建议

**先走 P0**：把 FX6 的可见帧问题收敛到“FX6 appFw 是否发布 OSD/GPE 帧”，而不是 QEMU 显示后端。现有 `-display none` + `pmemsave` 已能抓 FX3 的 640×480 UI，平台零改动。

只有在确实需要宿主窗口、且用户批准重建工具链时，才评估 P1（Cocoa）。`screendump`、VNC/SPICE 都不应作为第一选择。
