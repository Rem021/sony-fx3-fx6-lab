# FX6 运行时缺口与 FDAT/CBC 公开资料核查

日期：2026-11-06  
范围：FX6 在 FX3 固定平台上的启动研究，只读盘点 + 公开资料核查  
状态：**未解包、未修改 `BODYDATA.DAT`/任何固件；未启动新 VM；未改平台策略**

## 1. 结论摘要

1. 本机全盘只找到**一套** `libuxengine.so` / `libux_core.so` / `libgemini-grm.so`，位于 `nflasha15-files/lib`。没有找到第二套 FX6 版 ux/gemini 运行时。
2. 所有可用的 `libosal*` 里都**没有** `osal_alloc_sem_id` 的动态符号或普通符号；`libosal_uipc.so` 只导出 `check_dynamic_sem_id`。Spotlight 对 `osal_alloc_sem_id` 的命中全部是本项目 serial 日志，没有库实现。
3. 公开的 `ma1co/fwtool.py` 已完整给出 Sony 4th-gen FDAT 的 AES-CBC 结构：`CXD90045` 使用 `key_aes` + `key_cxd90045`，前 512 字节 AES-ECB key1，其余 AES-CBC key2，IV 位于数据尾部 `-0x110`。
4. FX6 首 512 字节用 `key_aes` 能解出 `UDTRFIRM 0100 U N`，与上述结构**部分吻合**；但 FX6 的 FDAT chunk 边界/尾部 `0x110` 语义仍有关键未知：按已知 `0x50`/`DEND=0xa534a5e` 算出的密文长度不是 16 字节对齐，不能直接宣称公开的 CBC 配方原样适用。
5. `GraphicsEngine` 构造失败与 OSAL 缺失是**两个独立但同层**的问题：前者是 FX6 图形单例链（`0x48800`/`0x487f8`/`libgemini-grm`）没有真实对象；后者是 `createScreen3D` 需要的 `osal_alloc_sem_id` 在现有库中不存在。

## 2. 本机只读盘点

### 2.1 方法

只使用文件名/符号/字符串查询，不执行固件解密，不写入任何被盘点目录：

- Spotlight 文件名查询：`mdfind -name ...`
- Spotlight 内容查询：`mdfind 'osal_alloc_sem_id'`
- 定向 `find`：`fx3-color-port-20261027`、`sony-firmware-20261024`、`outputs/sony-fx3-fx6-lab`
- 只读符号检查：`nm -D` / `nm`

### 2.2 目标库清单

| 路径 | 文件 | 大小（字节） | 结论 |
|---|---|---:|---|
| `.../FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib` | `libuxengine.so` | 742,128 | 全盘唯一 |
| 同上 | `libux_core.so` | 232,960 | 全盘唯一；导出 `uxengine_init2` |
| 同上 | `libgemini-grm.so` | 51,800 | 全盘唯一 |
| 同上 | `libosal_uipc.so` | 43,752 | 只导出 `check_dynamic_sem_id` |
| 同上 | `libosal_utm.so` | 10,216 | 无 sem 分配符号 |
| 同上 | `libosal_udate.so` | 27,344 | 无 sem 分配符号 |
| 同上 | `libosal_ulogio.so` | 40,168 | 无 sem 分配符号 |
| `.../input-20261028/engine-rootfs/2.04/usr/lib` | `libosal_*.so` | 35,528 / 47,848 / 40,168 / 10,216 | 只有 OSAL，无 ux/gemini |
| `.../input-20261028/engine-rootfs/2.05/usr/lib` | `libosal_*.so` | 同上 | 只有 OSAL，无 ux/gemini |
| `.../FX6-donor-assessment-20261103/team/donor/nested-files/nflasha1-initrd/usr/lib` | `libosal_*.so` | — | 只有 OSAL，无 ux/gemini |
| `.../sony-firmware-20261024/stage201-updater-request-endpoint/originals/7.02-main/lib` | `libObj.so` | 2,876,600 | **FX3 7.02**，不是 FX6 |
| 同上 | `libosal_uipc.so` | 43,752 | 只有 `check_dynamic_sem_id` |
| `.../sony-firmware-20261024/stage110-native-OSAL-envelope/inputs` | `libosal_uipc.so` | — | 只有 `check_dynamic_sem_id` |
| `.../sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/evidence/boot-request/originals/lib` | `libosal_utm.so`、`libosal_uipc.so` | — | 历史原件，无 sem 分配实现 |

补充：

- `stage201` README 明确写的是 **“FX3 7.02 更新请求”**，来源为 `nflasha15.img`（SHA256 `df0a2cf2...`）；因此 `7.02-main/lib` 不能当作 FX6 运行时。
- `engine-rootfs/2.04`、`2.05` 是历史 2.x 根文件系统，不是 FX6 主系统。
- Spotlight 查询 `libuxengine.so`、`libux_core.so`、`libgemini-grm.so` 各只返回 `nflasha15-files/lib` 一处。
- Spotlight 查询 `osal_alloc_sem_id` 只返回本项目的 `runs/cp-bind-*/serial.log`，没有返回任何库文件。

### 2.3 符号检查

```text
libosal_uipc.so:
  00000000000074d0 T check_dynamic_sem_id
  (no osal_alloc_sem_id)

libux_core.so:
  000000000002b964 T uxengine_init2
  (no osal_alloc_sem_id)

libuxengine.so:
  0000000000074e24 T _ZN8UXEngine6gfxengEv
  000000000008350c T _ZN2ux6gfxeng14GraphicsEngineC1Ev
  0000000000083290 T _ZN2ux6gfxeng14GraphicsEngine14createScreen3DERKNS_4core2IDE
  (no osal_alloc_sem_id)
```

`osal_alloc_sem_id` 目前只在以下场景出现：

- 多个库的日志字符串（`libCertificateManager`、`libInfraAdjMedia`、`libInfraMultiIF`、`libInfraNetworkCommon`、`libInfraRemote`、`libosal_udate` 等）；
- 本项目 VM serial 日志（`osal_alloc_sem_id() osalErr = -1023`）。

没有找到它的定义库。

## 3. FDAT/DAT 公开格式

公开来源是社区维护的 Sony 相机固件工具 [`ma1co/fwtool.py`](https://github.com/ma1co/fwtool.py)，其 `fwtool/sony/dat.py`、`fwtool/sony/fdat.py`、`fwtool/sony/constants.py`、`devices.yml` 是当前最完整的原始实现之一。Sony 官方支持页只提供固件下载/更新步骤，未公开 FDAT 容器或 AES 密钥；本次未找到官方 FDAT 规范。

### 3.1 DAT 外层

`dat.py`：

- 文件头 magic：`89 55 46 55 0D 0A 1A 0A`（`\x89UFU\r\n\x1a\n`）。
- 8 字节头之后是 chunk 序列，每个 chunk：
  - `size`：4 字节，大端；
  - `type`：4 字节，大端；
  - payload：`size` 字节。
- 关键 chunk：`DATV`、`PROV`、`UDID`、`FDAT`、`DEND`。
- `DEND` 是终止 chunk，payload 是 4 字节 CRC32；CRC 覆盖 `[0, fileSize - 8 - 4)`。

因此 `BODYDATA.DAT` 中的 `FDAT` 是 **DAT 容器里的一个 chunk**，不是独立文件。

### 3.2 FDAT 头

`fdat.py` 的 `FdatHeader`：

| 字段 | 大小 | 说明 |
|---|---:|---|
| `magic` | 8 | `UDTRFIRM` |
| `checksum` | 4 | 头部 CRC32 |
| `version` | 4 | `0100` |
| `modeType` | 1+3 | `U`（user） |
| `luwFlag` | 1+3 | `N`（normal） |
| 保留 | 8 | — |
| `versionMinor` / `versionMajor` | 1+1+2 | 版本 |
| `model` / `region` | 4+4 | 机型/区域 |
| 保留 | 4 | — |
| `firmwareOffset` / `firmwareSize` | 4+4 | 固件 tar 在 FDAT 内的偏移/大小 |
| `numFileSystems` | 4 | 文件系统数 |
| 保留 | 4 | — |
| `fileSystemHeaders[28]` | 28×12 | 每个 12 字节 |

`FdatHeader.size = 0x190`（400 字节）。`readFdat()` 会校验：

- `magic == UDTRFIRM`；
- `version == 0100`；
- `modeType == U`；
- `luwFlag == N`；
- 头部 CRC32（从第 12 字节到头部末尾）；
- 至少一个 `modeType == U` 的 file system header。

### 3.3 Crypter 选择

`fdat.py` 的 `_crypters`：

| 名称 | 类型 | 说明 |
|---|---|---|
| `CXD4105` / `MB8AC102` / `CXD4115` / `CXD4120` | SHA-1 流 | 1st gen |
| `CXD4132` | AES-ECB | 2nd gen |
| `CXD90014` | Double AES-ECB | 3rd gen |
| `CXD90045` | AES-CBC | 4th gen |

`CXD90045` 对应：

```python
AesCbcCrypter(key_aes, key_cxd90045)
```

### 3.4 AES-CBC 细节（`CXD90045`）

`AesCbcCrypter` 继承 `AesCrypter` / `BlockCrypter`：

- `decryptBlockSize = 1024`；
- 每个 1024 字节块先由 `BlockCrypter.unpackBlock` 处理：
  - 前 2 字节：16-bit little-endian 校验和；
  - 后 2 字节：`sizeAndEndFlag`，低 15 位是 payload 长度，最高位是最后一块标志；
  - 校验和 = 从第 3 字节到块尾的 16-bit LE 累加，`& 0xffff`；
  - 返回 `data[4:4+size]`。
- `decrypt(file)`：
  - 从文件末尾 `-0x110` 定位；
  - `size = 总长 - 0x110`；
  - 读 16 字节 IV（`data[-0x110:-0x100]`）；
  - 只解密前 `size` 字节，最后 `0x100` 字节不参与。
- `decryptBlock(data)`：
  - 第一块：前 512 字节用 **AES-ECB key1** 解密；
  - 第一块剩余 512 字节用 **AES-CBC key2** 解密；
  - 后续块全部用 **AES-CBC key2** 解密。

公开常量：

```text
key_aes       = E3 B0 C4 42 98 FC 1C 14 9A FB F4 C8 99 6F B9 24
key_cxd90014  = E8 B0 88 6D 97 18 4F 1F 65 C7 67 F7 93 99 65 BF
key_cxd90045  = C1 AA 8F 7C 46 34 1F FE D1 55 89 FC 81 70 A6 BB
                59 25 E8 5F 62 82 D7 F9 5B A3 FD F5 D3 03 E0 6B
```

这些 key 来自公开的 `fwtool/sony/constants.py`，不是从用户固件中提取的。

### 3.5 `CXD90014`（3rd gen，Double AES）

`DoubleAesCrypter(key_aes, key_cxd90014)`：

- 第一块前 512 字节只用 key1 解一次；
- 其余字节先用 key1 解，再用 key2 解（Double AES-ECB）；
- 不是 CBC，也没有 `0x110` IV trailer 逻辑。

如果 FX6 实际是 `CXD90014` 而不是 `CXD90045`，上面的 CBC 配方不适用。

## 4. FX6 与公开格式的吻合点与缺口

### 4.1 吻合点

本项目此前的只读观察：

- `BODYDATA.DAT` 的 FDAT chunk 位于 `0x50`；
- FDAT 数据起点 `0x58`；
- `DEND` 字符串位于 `0xa534a5e`；
- FDAT 首 512 字节用 `key_aes` 可解出 `UDTRFIRM 0100 U N`。

`key_aes` 正是 `CXD90045` 的 key1，且 `AesCbcCrypter` 的第一块前 512 字节就是 **key1 AES-ECB**。这与“首 512 字节能解出 `UDTRFIRM`”高度吻合，说明 FX6 **至少**使用了 `key_aes` 的 ECB 头部加密。

### 4.2 关键缺口：FDAT chunk 长度与 `0x110` trailer

`AesCbcCrypter` 要求：

```text
len(FDAT payload) - 0x110 - 0x200  是 16 的倍数
```

其中 `0x200` 是首 512 字节，`0x110` 是 IV + 尾部 0x100。

用已知偏移试算（FDAT 数据起点 `0x58`，`DEND` 字符串偏移 `0xa534a5e`）：

| 对 `DEND` 偏移的解释 | FDAT payload 长度 | 减 `0x310` 后 | mod 16 |
|---|---:|---:|---:|
| `DEND` 是 chunk 的 type 字段（chunk 头从 `D-4` 开始） | `0xa534a02` | `0xa5346f2` | 2 |
| `DEND` 是 chunk 的起始（size 字段） | `0xa534a06` | `0xa5346f6` | 6 |
| `DEND` 是 payload 起始（chunk 头从 `D-8` 开始） | `0xa5349fe` | `0xa5346ee` | 14 |

三种解释都**不是 16 字节对齐**。这意味着至少有一个前提不成立：

1. `DEND` 偏移不是 FDAT chunk 的精确边界；
2. FDAT payload 不是单个连续的 `AesCbcCrypter` 流；
3. `0x110` trailer 的语义/长度与公开工具不同；
4. FX6 使用了不同的块大小/尾部布局，或 `DEND` 与 FDAT 之间还有别的数据。

因此，**不能直接把 `fwtool` 的 `AesCbcCrypter` 套到 `BODYDATA.DAT` 上并宣称能解包**。必须先读取 `0x50` 处的 DAT chunk `size` 字段或重新核对 `DEND` 的 chunk 头，确定精确 payload 长度。

### 4.3 FX6 是否在 `devices.yml` 中

`devices.yml` 没有 `ILME-FX6`/`FX6` 条目。`CXD90045` 的已列机型包括：

- `DSC-HX99`、`DSC-RX0M2`、`DSC-RX10M4`、`DSC-RX100M5A`
- `ILCE-7M3`、`ILCE-7RM3`、`ILCE-7RM4`、`ILCE-9`、`ILCE-9M2`
- `FDR-AX700`、`ZV-1`、`ZV-E10`

FX6 是更新的电影机，可能仍用 `CXD90045`，也可能使用未收录的 5th-gen crypter。仅凭 `key_aes` 首 512 字节吻合，不能确定 key2/块格式。

## 5. 可行的解密/解包思路（需用户批准后执行）

以下步骤是**离线、只读、内存中**的验证计划；不修改 `BODYDATA.DAT`，不写回固件，不启动新 VM。

1. **只读 DAT 结构**
   - 读 `BODYDATA.DAT` 的 `0x00-0x60`，确认 magic、`DATV/PROV/UDID/FDAT/DEND` chunk 头。
   - 读 `0x50` 的 FDAT `size` 字段，得到精确 payload 长度，而不是靠 `DEND` 字符串猜。
2. **确定 FDAT payload 边界**
   - 计算 `fdat_start = 0x58`；
   - `fdat_end = fdat_start + size`；
   - 检查 `DEND` chunk 是否正好从 `fdat_end` 开始；如果不是，记录差值。
3. **检查 trailer**
   - `trailer = payload[-0x110:]`；
   - `iv = trailer[:16]`；
   - 检查 `payload_len - 0x110` 是否为 16 的倍数；
   - 如果不是，先不要解密，转为检查 `0x100` 尾部是否为签名/对齐填充，或 FDAT 是否还有二级 chunk。
4. **尝试 `CXD90045`**
   - 用 `key_aes` 解首 512 字节（AES-ECB）；
   - 用 `key_cxd90045` + `iv` 解剩余（AES-CBC）；
   - 按 `BlockCrypter` 去掉每 1024 字节块的 4 字节头；
   - 校验 `UDTRFIRM`、`0100`、`U`、`N`、头部 CRC32、file system header。
5. **回退候选**
   - 如果 `CXD90045` 失败，尝试 `CXD90014`（Double AES-ECB）；
   - 再尝试 `CXD4132`（AES-ECB）；
   - 记录每个候选的失败原因（magic/CRC/块校验/长度对齐）。
6. **成功后的只读展开**
   - 用 `readFdat()` 得到 `firmware.tar` 与 `updater.img` 的逻辑视图；
   - 只在临时目录/内存中列出 tar 成员，寻找 FX6 的 `libuxengine`/`libux_core`/`libgemini-grm`/OSAL；
   - 不写回 `BODYDATA.DAT`，不刷机。
7. **平台策略确认**
   - 即使解出 FX6 用户态库，是否允许把 FX6 用户态库放入 FX3 平台，仍需用户明确批准；
   - 平台（QEMU 机器、FX3 内核、DTB、设备模型）保持不变。

## 6. 仍缺的关键信息

1. FX6 的精确 crypter 代次（`CXD90045` 还是未收录的 5th gen）。
2. FX6 FDAT 的精确 chunk 长度与 `DEND` 边界；当前偏移算出的长度不满足 CBC 的 16 字节对齐。
3. `0x110` trailer 中最后 `0x100` 字节的语义（签名/填充/其它）。
4. FX6 是否使用 `BlockCrypter` 的 1024 字节块 + 4 字节块头；如果使用，块校验和/结束标志必须逐块验证。
5. FX6 的首 512 字节之后是否仍用 `key_cxd90045`，还是用了新 key。
6. 解出的用户态库是否与 FX6 appFw ABI 匹配；如果不匹配，仍不能解决 `GraphicsEngine`/`osal_alloc_sem_id` 问题。
7. `osal_alloc_sem_id` 的真实提供者；当前所有本机库都没有它。

## 7. 对当前 `GraphicsEngine` 阻塞的意义

已确认：

- `Application_System_Init` 可在 `app_ctx` 下返回；
- `uxengine_init2` 在 patch `0x48800`/`0x48810` 和 `libuxengine` getter 段后返回；
- `GraphicsEngine` 构造继续到：
  - `libux_core + 0x30e78`（`0x487f8` 空对象）；
  - `libgemini-grm + 0x8cc0`（`this=NULL` 写 `+0x230`）；
- `createScreen3D` 稳定打印 `osal_alloc_sem_id() osalErr = -1023` 并循环。

这些不是单靠 FDAT 解密就能自动解决的：即使解出 FX6 库，还需要替换/补齐 OSAL 和 `GraphicsEngine` 单例初始化链。反过来，如果只补 OSAL 而不换 ux/gemini，`GraphicsEngine` 构造仍会在 FX6 单例上空指针崩溃。

因此，下一步的最小闭环是：

```text
FX6 运行时库（OSAL + ux/gemini）
  + 正确的 GraphicsEngine 单例初始化
  + createScreen3D/drawFramebuffer
  + GPE/DMM 非零像素
```

## 8. 证据与来源

### 8.1 本机只读证据

- Spotlight：
  - `mdfind -name libuxengine.so` → 仅 `nflasha15-files/lib/libuxengine.so`
  - `mdfind -name libux_core.so` → 仅 `nflasha15-files/lib/libux_core.so`
  - `mdfind -name libgemini-grm.so` → 仅 `nflasha15-files/lib/libgemini-grm.so`
  - `mdfind 'osal_alloc_sem_id'` → 仅 `runs/cp-bind-*/serial.log`
- 符号：
  - `nm -D libosal_uipc.so` → `check_dynamic_sem_id`，无 `osal_alloc_sem_id`
  - `nm -D libux_core.so` → `uxengine_init2`，无 `osal_alloc_sem_id`
  - `nm -D libuxengine.so` → `GraphicsEngine::sys_getInstance`/`createScreen3D`/`drawFramebuffer`
- 历史 stage201：
  - `stage201-updater-request-endpoint/README.md` 标题为 “FX3 7.02 更新请求的实际接收者与写入边界”
  - `7.02-main/lib` 只有 `libObj.so`（2,876,600）和 `libosal_uipc.so`（43,752）

### 8.2 公开来源

- [`ma1co/fwtool.py`](https://github.com/ma1co/fwtool.py) — Sony 相机固件解包工具（社区原始实现）
- [`fwtool/sony/dat.py`](https://raw.githubusercontent.com/ma1co/fwtool.py/master/fwtool/sony/dat.py) — DAT/UFU/FDAT/DEND 容器
- [`fwtool/sony/fdat.py`](https://raw.githubusercontent.com/ma1co/fwtool.py/master/fwtool/sony/fdat.py) — FDAT 头、`CXD90045` AES-CBC、`CXD90014` Double AES
- [`fwtool/sony/constants.py`](https://raw.githubusercontent.com/ma1co/fwtool.py/master/fwtool/sony/constants.py) — `key_aes`、`key_cxd90014`、`key_cxd90045`
- [`devices.yml`](https://raw.githubusercontent.com/ma1co/fwtool.py/master/devices.yml) — 机型到 crypter 的映射；无 FX6 条目
- [Sony-PMCA-RE FDAT Generation（DeepWiki）](https://deepwiki.com/ma1co/Sony-PMCA-RE/4.1-fdat-generation) — 本次访问返回 HTTP 429，未能读到正文；仅作为索引记录
- Sony 官方 FX6 固件更新页（仅更新步骤/下载，无容器格式说明）：
  - [ILME-FX6 Ver.6.01（泰国）](https://www.sony.co.th/th/electronics/support/interchangeable-lens-camcorders-ilme-series/ilme-fx6v/software/00259042)
  - [ILME-FX6 Ver.6.01（意大利）](https://www.sony.it/electronics/support/interchangeable-lens-camcorders-ilme-series/ilme-fx6v/software/00259041)

### 8.3 边界声明

- 本报告没有对 `BODYDATA.DAT` 执行解密、解包、写回或刷机。
- 本报告没有启动新的 QEMU/VM。
- 本报告没有修改 FX3 平台、设备树、内核或 QEMU 参数。
- 本报告中的 key 来自公开开源常量，不是从用户固件提取的。
- 先前列出的三项待用户决策（提供 FX6 运行时库 / 允许从 FDAT 解包 / 平台策略确认）仍然有效。

## 9. 建议的下一步（等待用户批准）

1. **最小、只读的 FDAT 边界核查**：读取 DAT chunk `size`，确认 FDAT payload 精确长度，不解密。
2. 如果边界/对齐成立，执行一次内存中的 `CXD90045` 候选解密，只验证 `UDTRFIRM` + CRC，不落盘。
3. 如果 `CXD90045` 失败，按 `CXD90014` → `CXD4132` 回退，记录失败原因。
4. 成功后再决定是否提取 FX6 用户态库；提取也必须先得到用户对“平台保持 FX3、用户态换 FX6 库”的明确批准。
5. 无论 FDAT 是否成功，`osal_alloc_sem_id` 与 `GraphicsEngine` 单例初始化仍是独立的硬缺口。
