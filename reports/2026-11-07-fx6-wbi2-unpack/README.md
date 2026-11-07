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
