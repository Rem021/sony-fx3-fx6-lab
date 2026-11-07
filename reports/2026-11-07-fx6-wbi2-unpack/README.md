# FX6 BODYDATA / WBI2 解包进度

日期：2026-11-07  
范围：FX6 `BODYDATA.DAT` 的只读解包、`nflasha5` WBI2 内容、缺失运行时库定位  
状态：**只读解包；未启动/未改动 VM；未修改/重打包固件；未写 shim；未跑 pmemsave/解析器；未触碰用户三问**

## 1. 结论

1. `BODYDATA.DAT` **此前已经完整解包**，无需重复解密：
   - `firmware.fdat` 843,771,904；
   - `firmware.tar` 842,518,016；
   - `updater.img` 1,253,376；
   - `unpack-receipt.json` 记录了 model `0x91040086`、version `6.01`、CXD90057_k0 与各 SHA256。
2. 现有 `stage2` 只展开了 nflasha3/7/8/15；tar 里还有 **nflasha5 / nflasha23**。
3. `nflasha5` 是 **WBI2** 容器：
   - 202,677,056 字节；
   - 1197 段，64 字节/段，section table 在 202,338,816；
   - payload 从 0x200 连续存放，总 202,338,304；
   - 含 **7 处 `osal_alloc_sem_id`**，以及 `libosal_utm.so`、`libosal_uipc.so`、`libgrm.so`、`libuxengine.so` 字符串。
4. **缺失的 FX6 运行时库很可能就在 nflasha5**；本轮已把 WBI2 payload 按 load address 重建/提取，但**尚未隔离出独立的 `libosal_utm.so` ELF**，因此还不能直接 `nm` 验证 `osal_alloc_sem_id` 实现。
5. `nflasha23` 是 FAT32（MBR 分区从 sector 1 开始，67,108,864 字节）；尚未展开。

## 2. 已有解包 receipt

`team/donor/unpack-receipt.json`：

```text
model:  0x91040086
version: 6.01
crypter: CXD90057_k0
fdat:   843,771,904
tar:    842,518,016
updater:1,253,376
```

`firmware.tar` SHA256：

```text
53fe3dabbe23da2ddea9fa1a42d8c1a36e681ec90b6398fe4b903f5217aac099
```

## 3. nflasha5 WBI2

### 3.1 文件

```text
path: full-unpack-20261107/0700_part_image/dev/nflasha5
bytes: 202,677,056
sha256: d33f0bd9c305cd9217815cd1e1a4fd86ea48b28ddbbbe6c581c8665dc5fde2d1
magic: WBI2
```

`wbi2-receipt.json`：

```text
section_count: 1197
stored_data_bytes: 202,338,304
table_offset: 202,338,816
table_end: 202,415,424
```

### 3.2 段表

每段 64 字节：

```text
+0x00 load address (u32)
+0x08 size (u32)
+0x20 size (duplicate)
+0x28 load address (duplicate)
```

1197 段 size 总和：

```text
sum(sizes) = 202,338,304 = table_offset - 0x200
```

因此 payload 从 **0x200** 连续存放；`+0x00` 是 **load address**，不是文件偏移。按它直接 `pread` 会产生大量越界，这是第一轮提取的误区。

### 3.3 已提取

```text
full-unpack-20261107/wbi2-payload/
  1143 个非空段，总 202,338,304
  manifest.json
```

按 load address 重建的镜像：

```text
max load address: 0x24000000
image bytes:      603,979,776
```

### 3.4 osal 命中

`osal_alloc_sem_id` 在 7 个段：

```text
section 71   load 0x8b3f000  size 0x1c000
section 86   load 0x8cae000  size 0x2000
section 413  load 0xed80000  size 0x38000
section 470  load 0xfb60000  size 0x32000
section 732  load 0x1a8c8000 size 0x38000
section 795  load 0x1b250000 size 0x1e000
section 928  load 0x1ce17000 size 0x5000
```

其中 section 71 的字符串：

```text
[UDATE] %s osal_alloc_sem_id err=%d
```

同时可见：

```text
libosal_utm.so
libosal_uipc.so
libgrm.so
libuxengine.so
```

说明 nflasha5 **确实包含缺失的 OSAL/UX 运行时**。

### 3.5 尚未隔离 libosal ELF

在重建镜像里扫到 118 个 ELF header，但没有一个带 `libosal_utm.so` 的 `DT_SONAME`，也没有 `osal_alloc_sem_id` 动态符号。原因可能：

- WBI2 段是 **load-address 内存段**，一个 ELF 可能跨多个段；
- ELF header 可能在 osal 字符串之前的另一个 load 段，当前 `ELF` 解析切片/尺寸不完整；
- 段可能包含 **部分文件系统/压缩数据**，不能按独立 ELF 直接解析。

因此目前只能确认“库内容在 nflasha5”，还不能把 `libosal_utm.so` 作为可加载 ELF 取出。

## 4. nflasha23

```text
bytes: 67,108,864
file: DOS/MBR boot sector; partition 1 ID=0xb, startsector 1
```

FAT32；可用现有 `extract_fat32.py` 的 `PyFatFS(offset=512)` 逻辑展开。本轮未展开。

## 5. 实测 vs 推断 vs 缺失

### 实测

- BODYDATA 已解包 receipt；
- firmware.tar 的 nflasha5/23 存在与大小；
- nflasha5 WBI2 头、1197 段、table offset；
- sum sizes = table - 0x200；
- 1143 段 payload 已提取；
- 7 段含 `osal_alloc_sem_id`；
- `libosal_utm.so`/`libosal_uipc.so` 字符串存在；
- nflasha23 是 FAT32。

### 推断

- 缺失的 OSAL/UX 运行时在 nflasha5；
- `osal_alloc_sem_id` 的实现/包装可能在包含字符串的段或相邻 load 段；
- 需要按 load map 重建跨段 ELF，或找到段内的文件系统映射。

### 缺失

- `libosal_utm.so`/`libosal_uipc.so` 的独立 ELF 文件；
- `osal_alloc_sem_id` 的实际实现/导出符号；
- WBI2 段到文件/文件系统的完整映射；
- nflasha23 FAT32 内容；
- 运行时验证（未启动 VM）。

## 6. 下一步

1. 以 `wbi2-payload/manifest.json` 的 load address 为索引，找 osal 字符串所在段的**前一个/相邻 load 段**，检查是否含 ELF header；必要时把连续 load 段合并成文件。
2. 若 WBI2 段实际是文件系统镜像，按段内 `ext4/squashfs` 魔数重新识别；当前 1143 段中 14 个段以 `\x7fELF` 开头，可作为突破口。
3. 展开 nflasha23 FAT32，确认是否有配置/库补充。
4. 拿到 `libosal_utm.so` 后再用 `nm -D`/`readelf` 验证 `osal_alloc_sem_id`；仍不启动 VM。

## 7. 边界

- 未启动/改动任意 VM；
- 未修改/重打包 `BODYDATA.DAT` 或任意固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未写 shim/解析器代码（仅一次性只读提取脚本）；
- 未跑 pmemsave/解析器；
- 未触碰用户三问（FX6 运行时库 / FDAT 解包 / 平台策略）。

## 8. 更正：nflasha15 已有 libosal，但不导出 osal_alloc_sem_id

时间：2026-11-07。此更正不推翻 WBI2 解包结果，但修正“缺失库在 nflasha5”的表述。

### 8.1 已存在的 libosal

`nflasha15-files/lib/` 里早就有：

```text
libosal_utm.so   10K   sha256 a7ced89e...
libosal_uipc.so  43K   sha256 fe248d22...
libosal_udate.so 27K
libosal_ulogio.so 39K
```

都是 ELF64 AArch64 shared object。

### 8.2 但没有 osal_alloc_sem_id 导出

`nm -D`：

```text
libosal_utm.so  -> 无 osal_alloc_sem_id
libosal_uipc.so -> 只有 check_dynamic_sem_id (0x74d0)
```

进一步搜 `nflasha15-files`/`nested-files` 的 `.so`/`.ko`：

- 没有 `osal_alloc_sem_id` 的 `T/W` 定义；
- 只有若干 `.so` 里出现该字符串（日志/未解析引用）；
- 没有找到实际的导出实现。

### 8.3 WBI2 里的字符串是什么意思

`wbi2-payload` 的 7 处 `osal_alloc_sem_id`：

```text
[UDATE] %s osal_alloc_sem_id err=%d
```

这是 **libgrm 的错误日志字符串**，不是 `libosal_utm.so` 的导出符号。`libosal_utm.so`/`libosal_uipc.so` 的字符串多为 `DT_NEEDED` 名称或其他库的 dynstr，不能直接证明实现存在。

### 8.4 修正后的判断

- WBI2 payload 仍确认包含 `libosal_utm.so`/`libosal_uipc.so` 名称与 OSAL 错误日志；
- 但 **没有隔离出带有 `osal_alloc_sem_id` 导出的 ELF**；
- 既有 `nflasha15` 的 `libosal_utm.so`/`libosal_uipc.so` **也不导出该符号**；
- 因此“缺失库在 nflasha5”只能作为线索，不能作为已解决结论；
- 真正阻塞仍是：`osal_alloc_sem_id` 的 provider 尚未定位。

### 8.5 下一步

1. 检查 `nflasha15-files/kmod/osal_utm.ko`/`osal_uipc.ko` 是否以 kernel symbol/ioctl 形式提供 sem 分配；
2. 在 WBI2 payload 里优先找 **SONAME=libosal_utm.so** 的 ELF，而不是只搜字符串；
3. 若 WBI2 是 load-address 内存镜像，按段 flags/相邻关系重建完整库，而不是按段独立解析；
4. 仍不启动 VM、不跑 pmemsave。

## 9. 边界补充

本轮只读解包；原固件未改；没有运行 VM；没有写 shim/解析器；FDAT 解包已获准并执行，FX6 运行时库与平台策略两问仍未定。

## 10. OSAL sem 依赖复核

时间：2026-11-07。此节修正“OSAL provider 缺失”的优先级。

### 10.1 没有库导入/导出 osal_alloc_sem_id

搜 `nflasha15-files`、`nested-files`、`engine-rootfs` 的 `.so`/`.ko`：

```text
osal_alloc_sem_id 的 U/T/W 定义/引用：0
```

也就是说：

- 没有 FX6 用户态库 `U osal_alloc_sem_id`；
- 也没有库 `T/W osal_alloc_sem_id`；
- 之前看到的 `osal_alloc_sem_id` 字符串是 **libgrm 的错误日志文本**，不是动态符号。

### 10.2 实际使用的 sem API

`nflasha15-files/lib/libgrm.so`：

```text
U osal_sig_sem
U osal_stat_sem
U osal_wai_sem_tmo
```

`nflasha15-files/lib/libosal_uipc.so` 导出：

```text
T osal_sig_sem      0x4a70
T osal_stat_sem     0x4800
T osal_wai_sem_tmo  0x4858
T get_bsem          0x45b0
T check_dynamic_sem_id 0x74d0
```

`nflasha15-files/kmod/osal_uipc.ko` 也有：

```text
check_dynamic_sem_id
get_bsem
osal_sig_sem
osal_stat_sem
osal_wai_sem_tmo
```

所以 FX6 的 sem 供应链是 **osal_sig/stat/wai + get_bsem/check_dynamic_sem_id**，不是 `osal_alloc_sem_id`。

### 10.3 对此前 crash 的解释

此前 `GraphicsEngine` ctor 的 `osal_alloc_sem_id() osalErr=-1023` 不能由“FX6 缺少 libosal”解释：

- 当前 FX6 文件集里没有库导入该符号；
- 也没有库导出该符号；
- 因此这个调用很可能来自 **版本错配的 libuxengine**（FX3/stale/patched 副本），而不是当前 `nflasha15` 的 FX6 库。

### 10.4 优先级修正

- **OSAL provider 不是当前阻塞**；
- 真正阻塞仍是：
  - `GraphicsEngine::m_instance` 无静态写入；
  - `sys_createApplication`/`FrameBuffer::update` 未执行；
  - on-screen bitmap 未创建；
- 下一步应先核对 CPIO 里的 `libuxengine` SHA 是否等于 `nflasha15-files/lib/libuxengine.so`；若不等，说明跑的是错配库。

### 10.5 下一步

1. 对比 CPIO/运行时 `libuxengine`、`libgrm`、`libgemini-grm` 的 SHA 与 `nflasha15-files/lib`；
2. 若 SHA 不同，改用正确的 FX6 库；
3. 若 SHA 相同，再查 `GraphicsEngine` ctor 的 `osal_alloc_sem_id` 是否来自反汇编误读/旧日志；
4. 仍不启动 VM、不跑 pmemsave。

## 11. 边界

- 本轮只读解包；未改原固件；
- 未启动 VM；未改 QEMU/DTB/平台参数；
- 未写 shim/解析器；未跑 pmemsave；
- FDAT 解包已获准并执行；FX6 运行时库与平台策略两问仍未定。

## 12. libosal overlay 运行结果

时间：2026-11-07。为验证“CPIO 里 libosal 是 FX3 版”是否为 `osal_alloc_sem_id -1023` 的原因，做了两次受控运行。

### 12.1 CPIO 库哈希对照

CPIO `grmreal162`：

```text
libuxengine.so    11dbc9a7...  = nflasha15-files FX6 正确版
libgrm.so         0f9f9226...  = 正确版
libgemini-grm.so  f47c8f3e...  = 正确版
libux_core.so     c72d52b4...  = 正确版
libosal_utm.so    d9510b4c...  = FX3 版（非 nflasha15 a7ced89e）
libosal_uipc.so   09ebf598...  = FX3 版（非 nflasha15 fe248d22）
```

即：**核心 FX6 库正确，只有 libosal 是 FX3 版**。

### 12.2 overlay 实验

- 用 `nflasha15-files/lib` 的 4 个 FX6 libosal 做 overlay；
- 追加到原 CPIO 后生成：
  - `grmreal163-libosal.cpio`（`./usr/lib` 路径，未覆盖成功）
  - `grmreal164-libosal.cpio`（`usr/lib` 路径）
- 各自 150s、单 VM、`ap-window`。

两次结果：

```text
CP_RC0
appfw-launch: Application_System_Init returned
appfw-launch: uxengine_init2 returned
appfw-launch: GraphicsEngine ctor=...
osal_alloc_sem_id() osalErr = -1023  (x5)
APPFW_SEGV sig=11 addr=0x10
```

**行为没有变化**：

- 仍 5 次 `osal_alloc_sem_id -1023`；
- 仍在 GraphicsEngine ctor 后崩溃；
- overlay 未修复，且 overlay 是否真正覆盖 `/usr/lib/libosal*` 未能从串口确认。

### 12.3 解释

- FX6 libuxengine/libgrm/libgemini/libux_core 本身不导入 `osal_alloc_sem_id`；
- FX6 libosal 也不导出该符号；
- 错误字符串在 `libEsCodecLibrary.so`、`libInfraRemote.so`、`libosal_udate.so` 等库中出现，更像**别的库的日志**，不一定是 libosal 的返回值；
- 因此“换 libosal”不是充分修复；需要把 `APPFW_SEGV` 的 PC 映射到具体库/函数。

### 12.4 下一步

1. 在 appfw-launch 崩溃处理里打印 `/proc/self/maps` 或 `dladdr(pc)`，把 `pc=...` 落到具体 `.so+offset`；
2. 若 PC 在 libuxengine，查其符号/反汇编；若在 libgrm/libgemini，继续按前一份静态报告处理空成员；
3. 在明确函数前不再重复 overlay 运行；
4. 仍保持 FX3 平台/QEMU/DTB 参数不变。

## 13. 边界

- 本轮做了两次本地 VM 候选运行；未改原固件；
- 未改 QEMU 命令、DTB、平台参数；
- 未写 shim/解析器；未跑 pmemsave；
- FDAT 解包已获准并执行；FX6 运行时库与平台策略两问仍未定。

## 14. 调试 patch 迭代（167–170）

### 14.1 launcher maps-first patch

把 `appfw-launch` 的 `0x1018f6c b.ne` 改成 NOP（跳过 31 次寄存器打印）：
- overlay/全量重打均未可靠覆盖 `/usr/bin/appfw-launch`；
- 最后改为 **直接 patch CPIO 成员数据**，生成 167；
- 167 确认 `APPFW_PC_MODULE`/`APPFW_PC_MAP` 可以输出。

167 结果：

```text
APPFW_SEGV sig=11 addr=0x230 pc=... 
APPFW_PC_MODULE /usr/lib/libgemini-grm.so base=...
APPFW_PC_MAP ... libgemini-grm.so
```

即早期 crash = **libgemini-grm.so+0x8cc0**。

### 14.2 预 patch libgemini+0x8cc0

`0x8cc0` 指令：

```text
strb w19,[x20,#0x230]
```

x20=NULL，addr=0x230。把 CPIO 内 `libgemini-grm.so` 该 4 字节改成 NOP，生成 168。

结果：

```text
uxengine_init2 returned
patched gemini 0x8cc0 ...
GraphicsEngine ctor=...
```

**越过了早期 gemini 崩溃**，进入 GraphicsEngine ctor。

### 14.3 后续 crash

168 在 ctor 后新 crash：

```text
APPFW_SEGV addr=0x10 pc=... 
```

组合 launcher noloop + gemini patch（169）拿到：

```text
APPFW_PC_MODULE /usr/lib/libgrm.so base=...
pc offset = 0x22c28
```

`libgrm+0x22c28` = `FBResourceManager::getScreenRotate()` 内的：

```text
ldr w0,[x0,#8]
```

`bl 0x205b0` 返回的 x0 被当指针；addr=0x10。

把该 4 字节改成 NOP，生成 170。

### 14.4 170 结果

```text
uxengine_init2 returned
GraphicsEngine ctor=...
osal_alloc_sem_id -1023 x5
APPFW_SEGV addr=0x1b7f94027f8 pc=...
```

- crash 从 `libgrm+0x22c28` 转移；
- 但 170 的 handler 没输出 `PC_MODULE/PC_MAP`（可能 handler 自身在异常状态）；
- 尚未取得可见画面。

### 14.5 下一步

1. 用 169 的 maps-first handler 继续跑 170 的库 patch，拿新 PC_MODULE；
2. 若仍是空成员，继续 patch；
3. 每轮只加一个 NOP，保持 FX3 平台/QEMU/DTB 不变；
4. 直到 `createScreen3D` 返回非 NULL，再做 OSD ring 抓帧。

## 15. 边界

- 上述只改本地候选 CPIO 的库/launcher 字节；原固件未改；
- QEMU 命令/DTB/平台参数未改；
- 未跑 pmemsave；未写 shim；
- FDAT 解包已获准并执行；FX6 运行时库与平台策略两问仍未定。

## 16. 171/172：getScreenRotate 与 dladdr 后的新崩溃

### 16.1 getScreenRotate 早返回

170 把 `libgrm+0x22c28` 改成 NOP 后，handler 没输出 maps。171 改为在函数入口：

```text
0x22c18: mov w0, #0
0x22c1c: ret
```

即 `FBResourceManager::getScreenRotate()` 直接返回 0，绕过整个函数。

结果仍无 maps，但 crash PC 转成：

```text
pc=0x7f78d3ce44
GraphicsEngine ctor=0x7f78d4450c
```

用 ctor 偏移 `0x8350c` 反推 libuxengine base：

```text
base = 0x7f78cc1000
pc offset = 0x7be44
```

`libuxengine+0x7be44` 符号：

```text
pgList<pgMap<ux::core::ID, ux::gfxeng::ScreenBase*>::MapItem>::Item::Leave()
```

说明已经进入 **screen map 列表**，但列表/节点为空或已损坏。

### 16.2 dladdr 跳过

172 在 169 的 maps-first handler 基础上，把两个 `bl dladdr` 改成 `mov w0,#0`，试图跳过 dladdr、直接读 `/proc/self/maps`。

结果：

```text
APPFW_SEGV addr=0x1b7f94027f8 pc=0x7f78d3ce44
APPFW_X0=...
```

handler 仍只输出 X0 后截断，maps 未出。说明崩溃上下文已不适合在 handler 里继续调用 libc。

### 16.3 修正后的判断

- 早期 `libgemini+0x8cc0` 已绕过；
- `FBResourceManager::getScreenRotate` 已早返回；
- 现在 crash 在 **`libuxengine+0x7be44` 的 `pgList::Leave()`**，属于 screen map 容器；
- 不是单纯空成员 write，而是 **列表节点/容器状态** 问题；
- 继续 NOP 单条指令的收益下降，需要看 `pgList::Leave()` 的调用点和 `ScreenBase*` map 的构建。

### 16.4 下一步

1. 反汇编 `libuxengine+0x7be44`，看 `Leave()` 对 `this` 的解引用；
2. 找 `pgList::Leave()` 的调用点（`createScreen3D`/`Screen3D` 构造）；
3. 若 `this` 来自未初始化的全局/空 map，补初始化或跳过该 screen map 操作；
4. 仍保持 FX3 平台/QEMU/DTB 不变。

## 17. 边界

- 候选 CPIO 只改本地库/launcher 字节；原固件未改；
- QEMU 命令/DTB/平台参数未改；
- 未跑 pmemsave；未写 shim；
- FDAT 解包已获准并执行；FX6 运行时库与平台策略两问仍未定。
