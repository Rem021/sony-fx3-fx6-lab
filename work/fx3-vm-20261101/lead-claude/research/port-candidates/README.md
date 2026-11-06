# Sony 固件/功能移植到经典 FX3：平台候选比较

核查日期：2026-11-03；目标为经典 **ILME-FX3**。比较 8 个候选与 FX3 基线，只做 Sony 官方公开资料和 GPL 源码静态核查。

**优先研究 FX3A，其次 A7S III，再次 FX30；FX5 是本组中跨平台差异最大的整套系统供体。** 其他候选的主 GPL 都落在 CXD90057 / Cortex-A35 ×4 / GIC-400 / Linux 4.9.337 这一公开源码基线，不能仅凭“较新机型”或“BIONZ XR”判断它们换了应用处理器平台。下面的排序是工程推断（B），并不表示任何机型可直接互刷。

**若目的只是 BIG6 六宫格主页，经典 FX3 已有原生实现。** Sony 的说明明确列出 FX3 Ver.7.00、FX3A Ver.2.00、FX30 Ver.6.00 的 BIG6 门槛；无需以跨机型固件作为此前提。本轮仅核对说明，没有下载更新包或操作机身。[Sony 官方说明](https://www.sony.com/zh-cn/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx30/articles/00365338)

## 证据范围与读法

- **A**：直接读取的 Sony 分发源码、文件哈希/行号，或 Sony 官方规格/发布/支持页。源码结论只覆盖该型号关联的公开包及所查示例配置。
- **B**：平台/硬件差异的工程解释、候选排序，以及明确标出的“规格未列”推断。
- **未知**：实际机身选用的 DTB/defconfig、硅片修订、专有 HAL/IPC/ISP、校准、签名和存储密钥状态。公开文件相同不等于实际配置或二进制兼容。

先读了用户指定的 [Stage133 方法先例](../../../../sony-firmware-20261024/stage133-FX5-source-availability-and-portability/README.md) 与 `code-portability-review.json`，再重新读取/哈希 FX3 与 FX5 已有本地 GPL 原包，并从各机型官方开源页取得本次表内版本。版本选自本次 [B2B 索引](https://oss.sony.net/Products/Linux/B2B/category01.html) / [DI 索引](https://oss.sony.net/Products/Linux/DI/category01.html)；不是声称所有地区当前机身固件的最新版本。

## 主平台矩阵（A：型号关联公开源码）

| 机型 / 所查 GPL 页 | SoC compatible | CPU / DTS 核数 | GIC | 内核 Makefile | 所查示例 TEE | OP-TEE / crypt_emmc 节点 |
|---|---|---|---|---|---|---|
| [ILME-FX3](https://oss.sony.net/Products/Linux/B2B/ILME-FX3_Ver700.html) Ver.7.00 | `cxd,cxd90057` | cortex-a35 ×4 | `arm,gic-400` | 4.9.337 | 未启用 | 所查主 dtsi 未见 / 未见 |
| [ILME-FX3A](https://oss.sony.net/Products/Linux/B2B/ILME-FX3A_Ver200.html) Ver.2.00 | `cxd,cxd90057` | cortex-a35 ×4 | `arm,gic-400` | 4.9.337 | 未启用 | 所查主 dtsi 未见 / 未见 |
| [ILCE-7SM3](https://oss.sony.net/Products/Linux/DI/ILCE-7SM3_Ver500.html) Ver.5.00 | `cxd,cxd90057` | cortex-a35 ×4 | `arm,gic-400` | 4.9.337 | 未启用 | 所查主 dtsi 未见 / 未见 |
| [ILME-FX30](https://oss.sony.net/Products/Linux/B2B/ILME-FX30_Ver600.html) Ver.6.00 | `cxd,cxd90057` | cortex-a35 ×4 | `arm,gic-400` | 4.9.337 | 未启用 | 所查主 dtsi 未见 / 未见 |
| [ILME-FX6V/FX6T](https://oss.sony.net/Products/Linux/B2B/ILME-FX6V_Ver600.html) V6.00 | `cxd,cxd90057` | cortex-a35 ×4 | `arm,gic-400` | 4.9.337 | 未启用 | 所查主 dtsi 未见 / 未见 |
| [ILCE-7M4](https://oss.sony.net/Products/Linux/DI/ILCE-7M4_Ver600.html) Ver.6.00 | `cxd,cxd90057` | cortex-a35 ×4 | `arm,gic-400` | 4.9.337 | 未启用 | 所查主 dtsi 未见 / 未见 |
| [ILME-FX2B/FX2](https://oss.sony.net/Products/Linux/B2B/ILME-FX2BFX2_V100.html) V1.00 | `cxd,cxd90057` | cortex-a35 ×4 | `arm,gic-400` | 4.9.337 | 未启用 | 所查主 dtsi 未见 / 未见 |
| [ILCE-1](https://oss.sony.net/Products/Linux/DI/ILCE-1_Ver400.html) Ver.4.00 | `cxd,cxd90057` | cortex-a35 ×4 | `arm,gic-400` | 4.9.337 | 未启用 | 所查主 dtsi 未见 / 未见 |
| [ILME-FX5](https://oss.sony.net/Products/Linux/B2B/ILME-FX5.html) 未标机身版本的 GPL 页 | `cxd,cxd90xxx` | cortex-a53 ×4 | `arm,gic-v3` | 5.15.179 | 启用 | 有 / 有 |

上表的 CXD90057 行读取 `arch/arm64/boot/dts/cxd/cxd90057.dtsi`，CPU 在 93/102/111/120 行，GIC 在 133 行，根 compatible 在 42 行；示例 `cxd90057_set_defconfig` 的 `CONFIG_NR_CPUS=4` 与 `# CONFIG_TEE is not set` 另有行号证据。FX5 读取 `cxd90xxx.dtsi`，相应根/CPU/GIC/OP-TEE 在 37、109/118/127/136、149、185 行，`crypt_emmc_init` 在 1117 行；`cxd90201_set.dts` 引用该 dtsi，示例 `cxd90201_set_defconfig` 开启 TEE/OP-TEE。这些字符串不独立证明 FX5 实装硅片的完整商业料号。

FX5 既有 `cemmc-init` 公开代码还直接调用 TEE context/session/invoke 和 eMMC 密钥初始化接口，已重新哈希并保留三份选段。[本地源码证据](FX5-secure-storage-local-evidence.json) 证明存在安全存储初始化支持；**不证明任何实机当前加密布局或已取得解密/签名能力**。同样，FX3 等示例 TEE 关闭、主 dtsi 无 crypt_emmc，不等于物理机身完全没有安全世界或加密。

### 共享文件与另列的 kernel-u

| 主包机型 | 主 dtsi 与 FX3 字节相同 | 示例 defconfig 相同 | 根 Makefile 相同 |
|---|---|---|---|
| 经典 FX3 | 是 | 是 | 是 |
| FX3A | 是 | 是 | 是 |
| A7S III | 是 | 是 | 是 |
| FX30 | 是 | 是 | 是 |
| FX6 | 是 | 是 | 是 |
| A7 IV | 是 | 是 | 是 |
| FX2 | 是 | 是 | 是 |
| A1 / α1 | 是 | 是 | 是 |
| FX5 | 否 | 否 | 否 |

该相同比较是逐文件 SHA-256，不把整个源包视为相同，也不把通用 SoC dtsi 当作完整型号板卡描述。包里另有 FPGA/QEMU 的 A35/A53 示例；它们没有用于上表的机身平台判定。完整文件哈希和原行在 [source-analysis.json](source-analysis.json) 与 [platform-matrix.json](platform-matrix.json)。

| 官方另列包 | 内核 | 其中主平台示例 | 状态 |
|---|---|---|---|
| [FX6 linux-kernel-u](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel-u.tar.gz) | 4.9.186 | `cxd,cxd90057` / arm,cortex-a35 ×4 / `arm,gic-400` | 用途、是否选用未知 |
| [FX2 linux-kernel-u](https://prodgpl.blob.core.windows.net/download/B2B/2025062401_ILMEFX2BFX2_V100/linux-kernel-u.tar.gz) | 4.9.186 | `cxd,cxd90057` / arm,cortex-a35 ×4 / `arm,gic-400` | 用途、是否选用未知 |

`-u` 只是公开包名，本轮没有构建/启动它，也没有证据把它解释为额外物理 CPU、当前相机内核或独立子系统。不得因为一个 GPL 页面列了两个内核就推定有两套硬件平台。

## 硬件规格对照

像素单位为 MP（百万）；“静/影/总”分别是官方列出的静态有效、视频有效、总像素，`?` 表示该项在所查表中没有单列。传感器“型号”列只写官方 Exmor 类别；**精确 IMX 料号均未从这些官方来源核实**，像素相近不当作同一颗传感器。

| 机型 / 规格来源 | 发布/修订年 | 传感器类型与像素：静 / 影 / 总 MP | IBIS | EVF | SDI | 内置 ND | 卡槽 |
|---|---|---|---|---|---|---|---|
| [经典 FX3](https://www.sony.jp/pro-cam/products/ILME-FX3/spec.html) | 2021 | 35mm 全画幅 Exmor R CMOS，35.6 × 23.8 mm；12.1 / 10.3 / 12.9 | 5轴 | 无内置 EVF* | 未列* | 未列* | 2 × CFexpress Type A / SD UHS-II 复合槽 |
| [FX3A](https://www.sony.jp/pro-cam/products/ILME-FX3A/spec/) | 2025（型号修订） | 35mm 全画幅 Exmor R CMOS，35.6 × 23.8 mm；12.1 / 10.3 / 12.9 | 5轴 | 无内置 EVF* | 未列* | 未列* | 2 × CFexpress Type A / SD UHS-II 复合槽 |
| [A7S III](https://www.sony.jp/ichigan/products/ILCE-7SM3/spec.html) | 2020 | 35mm 全画幅 Exmor R CMOS，35.6 × 23.8 mm；12.1 / ? / 12.9 | 5轴 | 内置 0.64 英寸 OLED，9,437,184 dots | 未列* | 未列* | 2 × CFexpress Type A / SD UHS-II 复合槽 |
| [FX30](https://www.sony.jp/pro-cam/products/ILME-FX30/spec.html) | 2022 | APS-C / Super35 Exmor R CMOS，23.3 × 15.5 mm；26 / 20.1 / 27 | 5轴 | 无内置 EVF* | 未列* | 未列* | 2 × CFexpress Type A / SD UHS-II 复合槽 |
| [FX6](https://www.sony.jp/pro-cam/products/ILME-FX6V/specification.html) | 2020 | 35mm 全画幅 Exmor R CMOS；? / 10.26 / 12.9 | 无 | 无内置 EVF；原配 3.5 英寸 LCD 不是 EVF | 12G/6G/3G/HD | 电子可变 1/4–1/128 | 2 × CFexpress Type A / SD UHS-II 复合槽 |
| [A7 IV](https://www.sony.jp/ichigan/products/ILCE-7M4/spec.html) | 2021 | 35mm 全画幅 Exmor R CMOS，35.9 × 23.9 mm；33 / ? / 34.1 | 5轴 | 内置 0.5 英寸 OLED，3,686,400 dots | 未列* | 未列* | 槽1 CFexpress Type A / SD UHS-II；槽2 SD UHS-II |
| [FX2](https://www.sony.jp/pro-cam/products/ILME-FX2B/spec.html) | 2025 | 35mm 全画幅 Exmor R CMOS，35.9 × 23.9 mm；33 / 27.6 / 34.1 | 5轴 | 内置可俯仰 0.5 英寸 OLED，3,686,400 dots | 未列* | 未列* | 槽1 CFexpress Type A / SD UHS-II；槽2 SD UHS-II |
| [A1 / α1](https://www.sony.jp/ichigan/products/ILCE-1/spec.html) | 2021 | 35mm 全画幅堆栈式 Exmor RS CMOS，35.9 × 24.0 mm；50.1 / ? / 50.5 | 5轴 | 内置 0.64 英寸 OLED，9,437,184 dots | 未列* | 未列* | 2 × CFexpress Type A / SD UHS-II 复合槽 |
| [FX5](https://www.sony.jp/pro-cam/products/ILME-FX5/spec.html) | 2026（宣布；上市延期） | 35mm 全画幅堆栈式 Exmor RS CMOS，35.9 × 24.0 mm；? / ? / 18.2；有效最大16.6 | 5轴 | 机身不内置；可选外置 DVF-EL1，0.58 英寸 OLED，约707万 dots | 未列* | 未列* | 2 × CFexpress 2 Type A / SDXC UHS-II 复合槽 |

`*` 为 B：从所查官方完整规格/接口表未列该内置项作出的比较用推断，JSON 留为未知，不作拆机层面的绝对排除。没有把远程 App 的 ND 控制栏是否支持当成物理 ND 存在与否的依据。IBIS、像素、列明的 EVF 和卡槽为 A；FX6 无 IBIS 还由 [Sony 官方访谈](https://www.sony.jp/ichigan/a-universe/news/750/) 明确说明。FX6 的原配 LCD 不是电子取景器；FX5 可配外置 EVF 也不等于机身内置。

FX3A 确实存在，[Sony 支持页](https://support.sony.jp/electronics/support/articles/00376946) 将 2025 年 5 月 FX3 停售与 FX3A 型号替换直接关联；本轮未定位精确的全球首销日。FX3A 的屏幕为 2,359,296 dots，经典 FX3 规格约 144 万 dots；即使其他公开规格接近，显示链和板级器件仍不能假设相同。

FX5 在 [2026-07-22 公告](https://www.sony.jp/CorporateCruise/Press/202607/26-0722B/) 发布，随后 [2026-08-18 延期通知](https://www.sony.jp/pro-cam/info2/20260818.html) 撤回原上市日；本次读取的 [产品页](https://www.sony.jp/pro-cam/products/ILME-FX5/) 仍标 Coming Soon / 发售日未定。因此表中 2026 是宣布年，不能写成已在日本实际上市的确认年份。

各机型发布年份来源：[经典 FX3](https://www.sony.jp/CorporateCruise/Press/202102/21-0224/)、[A7S III](https://www.sony.jp/CorporateCruise/Press/202007/20-0729/)、[FX30](https://www.sony.jp/CorporateCruise/Press/202209/22-0928/)、[FX6](https://www.sony.jp/CorporateCruise/Press/202011/20-1118/)、[A7 IV](https://www.sony.jp/CorporateCruise/Press/202112/21-1202/)、[FX2](https://www.sony.jp/CorporateCruise/Press/202505/25-0528/)、[A1 / α1](https://www.sony.jp/CorporateCruise/Press/202101/21-0127/)、[FX5](https://www.sony.jp/CorporateCruise/Press/202607/26-0722B/)。所有抓取 URL、时间、原 HTML SHA-256 与选段行号汇总于 JSON。

## 移植难度排序（B：由易到难；全部仍缺二进制/实机证据）

比较对象是“把整套系统或成像相关功能搬到经典 FX3 的相对工程工作量”；权重依次是主平台、成像硬件、外设/操控与私有应用依赖。没有可量化的成功概率。

| 顺位 | 候选 | 理由及较合理的研究用途 |
|---|---|---|
| 1 | FX3A | 所查 GPL 平台与 FX3 相同；官方规格的传感器类别、尺寸、像素、IBIS、双复合卡槽和机身用途最近。LCD 从约144万变为2359296 dots、型号标识及潜在器件修订仍需适配，不能直接互刷。 **用途：**显示/资源和同系列应用差异研究；新增功能收益可能有限。 |
| 2 | A7S III | 同类 12.1MP 全画幅、相同尺寸和总像素，IBIS/双复合槽接近；所查 GPL 平台相同。EVF、操控、冷却和消费级静态/视频应用路径与 FX3 不同，官方规格不能证明同一传感器料号。 **用途：**同代图像/录制控制逻辑比较。 |
| 3 | FX30 | 所查 GPL 平台相同，Cinema Line 操控、冷却、IBIS 和双复合槽接近；APS-C 26MP / 视频20.1MP 与 FX3 的低像素全幅相差很大，传感器读出和 ISP 标定不能照搬。 **用途：**菜单/界面/操作资源参考优先于成像链移植。 |
| 4 | FX6 | 所查主平台及低像素全幅规格接近；但 FX6 无机身 IBIS、带 SDI/可变 ND、专业接口和录制/控制路径不同，并另附 kernel-u 源码。ND/SDI 是 FX3 缺少的硬件，不能靠固件获得。 **用途：**专业菜单/录制状态机参考；若只研究成像链，可提高优先级。 |
| 5 | A7 IV | 所查 GPL 平台相同、全幅和 IBIS 接近；33MP 读出/ISP、EVF、无风扇机身与单 CFe 槽布局不同。保留 FX3 成像驱动的单项 UI 研究可排在 FX6 前。 **用途：**同代应用机制研究，不提供高像素/超采样硬件能力。 |
| 6 | FX2 | 主 GPL 仍为 CXD90057/A35/GIC-400/4.9.337；33MP/视频27.6MP、AI 处理单元、俯仰 EVF、单 CFe 槽、控制/流媒体依赖有差异。另列的 kernel-u 版本不证明另一颗处理器或实际选用状态。BIG6 是较近的 UI 参考，AI 能力不能预设可移植。 **用途：**UI 布局参考；单项 UI 可排在 A7 IV/FX6 前。 |
| 7 | A1 / α1 | 所查主 GPL 平台接近仍不抵消 50.1MP 堆栈传感器、8K/高速读出、EVF 和相应 ISP/缓冲链差异。静态平台共性只支持源码比对。 **用途：**同代基础组件和接口比较。 |
| 8 | FX5 | A53/GIC-v3/5.15 + OP-TEE/crypt_emmc 与 FX3 的 A35/GIC-400/4.9 示例明确跨平台；BIONZ XR2、新堆栈传感器、显示、电池、网络/音频架构也不同。属于完整 BSP/安全世界/专有 HAL 适配。 **用途：**仅作产品/交互参考，当前最不适合整套系统供体。 |

**中段不是稳定的绝对名次。** FX6 / A7 IV、FX2 / A1 会随待移植的具体功能改变顺序：只比较 UI，FX2/FX30 的 Cinema Line 操作资源更有价值；只比较低像素全幅成像链，FX6 的研究顺位可以上升。FX2 的 AI、A1 的 8K/高速堆栈读出、FX6 的 ND/SDI、FX5 的新传感器/安全世界，不会因共享 ARM64 或菜单资源而变成 FX3 硬件能力。

## 未关闭的关键问题

1. FX3 参考是 Ver.7.00 GPL，不是对用户 7.02 当前 boot/DTB/ELF/内核配置的同机指纹读取；其他机型也只覆盖表内公开源码版本。
2. 仍未知每款机身实际所选 DTB、内存映射、板级修订、传感器料号/时序、协处理器固件及标定。完整相同 dtsi/defconfig 也不能消除这些缺口。
3. 未取得或比较本轮供体完整机身固件、专有应用/HAL/IPC/ISP、分区和启动签名链；因此没有二进制兼容结论、可刷包或刷写放行。
4. 未确认任何机身当前 TEE、eMMC 加密、密钥或恢复入口；不从公开示例配置推演已可解密、重签或跨机刷写。
5. 精确传感器 IMX 料号、本次“规格未列”项及 FX5 最终上市日仍保留未知。
6. 同平台候选的下一项可复核工作应围绕一个明确功能比较其依赖和硬件前提；“最近供体”本身不能回答是否真的增加目标录制模式。

## 下载与复核记录

只获取 Linux GPL 源码包以读取根 Makefile、Sony DTS/DTSI、defconfig；FX3/FX5 复用现有本地原包并重新哈希。**没有下载或修改相机固件更新包，没有触碰相机、VM/runtime，没有执行下载的 Sony 代码。** 新抓取包以 1 MiB HTTP Range 完整顺序组装，用服务器长度、Content-MD5 和本地完整 SHA-256 检查；中断/重试的输出未当作成功包。

| 机型 / 源包直链 | 完整字节数 | SHA-256 |
|---|---:|---|
| [A1 / linux-kernel](https://prodgpl.blob.core.windows.net/download/DI/20251210_ILCE-1_Ver.4.00/linux-kernel.tar.gz) | 109990699 | `b0b6e349142428eee8f18d18ac35d1970b17ecbd120654c71e8b7057fe11ee87` |
| [A7IV / linux-kernel](https://prodgpl.blob.core.windows.net/download/DI/ILCE-7M4_Ver.6.00/linux-kernel.tar.gz) | 109985000 | `e9f708acebf62bd5659cc578101db0d9aa308a4fc413586502451e8a58c80b0e` |
| [A7SIII / linux-kernel](https://prodgpl.blob.core.windows.net/download/DI/ILCE-7SM3_Ver.5.00/linux-kernel.tar.gz) | 109992864 | `ea5f9984546be55944cf4ea39700f9767a9df0b61372e9bbcbc086485bed504f` |
| [FX2 / linux-kernel-u](https://prodgpl.blob.core.windows.net/download/B2B/2025062401_ILMEFX2BFX2_V100/linux-kernel-u.tar.gz) | 108790863 | `73cb30ba66cb3128a8d39de360f15ff746f75e60a7250e60d94697e21a61160b` |
| [FX2 / linux-kernel](https://prodgpl.blob.core.windows.net/download/B2B/2025062401_ILMEFX2BFX2_V100/linux-kernel.tar.gz) | 109976523 | `f08d5be79385e2514aebe9fc5ea1d1b943bcb773dd5ce4218489011f94c56018` |
| [FX3 / linux-kernel](https://prodgpl.blob.core.windows.net/download/B2B/ILME-FX3_Ver.7.00/linux-kernel.tar.gz) | 109987145 | `bb2d9cc676fef6aaf2f8f6703c4e041c133da0e7101b5afd33800eaf7c156d0f` |
| [FX30 / linux-kernel](https://prodgpl.blob.core.windows.net/download/B2B/ILME-FX30_Ver.6.00/linux-kernel.tar.gz) | 109982872 | `ee8903a93e09a1be9624d7c7edd497cfbff25429a1027a95b5cdc79943c642f1` |
| [FX3A / linux-kernel](https://prodgpl.blob.core.windows.net/download/B2B/ILME-FX3A_Ver.2.00/linux-kernel.tar.gz) | 109983268 | `08700a4967e318bb01374f47e3d1e0096953a4047243b52517c32af6751db54d` |
| [FX5 / linux-kernel](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/linux-kernel.tar.gz) | 151522353 | `1e1cf32816e841462bd1d0f4e93c4897a44d0a9b95641387c74cafb6d6f44190` |
| [FX6 / linux-kernel-u](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel-u.tar.gz) | 108790863 | `73cb30ba66cb3128a8d39de360f15ff746f75e60a7250e60d94697e21a61160b` |
| [FX6 / linux-kernel](https://prodgpl.blob.core.windows.net/download/B2B/2026031201_ILME_FX6_V600/linux-kernel.tar.gz) | 109952792 | `2e5bdfa72018cef6bdfa209635794973d7266c7ee657db094c7ee2c414dbcc42` |

已有 FX5 `cemmc-init` 复核原包 SHA-256：`16b07a4b638c0fd8dcf846a2ffb3672825bf9f84415513ba09dbc74d5a93b4c0`；[来源直链](https://prodgpl.blob.core.windows.net/download/B2B/20260731_ILME-FX5/cemmc-init.tar.gz)。此包本轮仅本地读取。

交付与证据入口：

- [platform-matrix.json](platform-matrix.json)：9 行机型、主平台、源码原行/文件哈希、硬件规格、B 级排序、全部来源 URL/下载 SHA 与未知项。
- [source-analysis.json](source-analysis.json)：11 份内核源码包的 Makefile / DTS / defconfig 选段索引。
- [page-receipts.json](page-receipts.json)、[spec-page-receipts.json](spec-page-receipts.json)、`receipts/`：官方页 HTML 摘要和每包长度、Content-MD5/完整 SHA-256、提取成员摘要。
- `source-excerpts/`：未执行的 Sony 平台源码选段；`pages/`：公开 HTML 与 UTF-8 可读文本；`gpl-archives/`：本轮取得的 Linux GPL 临时原包。
- `collect_sources.py` / `range_collect.py` / `collect_specs.py` / `analyze_sources.py` / `build_matrix.py` / `build_readme.py`：只读公开抓取、选段和报告生成脚本，写入均限于本目录。

复核状态：完整包和选段的 SHA-256、JSON 可解析性、9 机型/11 内核包覆盖与本地证据链接在 [validation.json](validation.json) 登记。这是静态资料验收，没有构建、启动、实机或功能移植验收。
