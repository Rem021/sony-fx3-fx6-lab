# FX3 原生 VENICE 色彩数据与控制链逆向

本轮继续用户要求的实际解包与实现研究。分析对象为已固定摘要的经典 FX3 7.02 `av-cam.bin`，不改 H.265 任务、相机或其他研究工作树。任务目录沿用创建时的 20261027 命名，后续验证跨日继续写在这里。

**已恢复真实矩阵、1D 与 3D 数据，并执行原始初始化、配置查询、DMA 链表生产和设置前端的受限离线仿真。现在有了数值和装载代码的实现起点，尚未完成菜单接入或实际录像像素验证。**

## 这轮恢复了什么

| 对象 | 已恢复内容 | 复核方式 |
|---|---|---|
| 描述符 | 612 个符合固定布局的 MLUT 数据记录；其中 30 个带 VENICE 名称 | 原数据指针、寄存器偏移、word count、字符串及邻接边界 |
| 矩阵 | 9 个系数，signed 19-bit/Q16 解释；每行整数和为 65536 | 同包 THRU 为对角 65536，TEST 为 0x7ffff；另与 Sony 官方 VENICE IDT 独立对照 |
| 1D 表 | 每通道 256 个 32 位打包字，可展开为 512 个 16 位槽；RGB 相同 | 原字节和摘要；前 511 槽单调，末槽为 0，未擅自删除或当均匀采样曲线 |
| 3D 表 | 24 个 bank，共 20×20×20 节点、24,000 通道值 | 对同包 THRU 的全部节点检验，24,000 值逐一精确相等 |
| 配置表 | 原查询函数识别 29 个内置配置 | 32 个输入：1–29 成功，0、-1、30 不命中，输出前后哨兵保持 |
| 装载数据 | 原函数产生 70 项 DMA linked-list 描述符 | 两组声明地址映射输入下，逐项检查源、目标、next、count/control 与末项终止位 |
| 设置入口 | 原前端接受 IP=0/look=22 并到达原队列入口 | 在进入队列函数前停止；另测 look=0/30 与 IP=1，均原生返回 -13 |

提取脚本读取的镜像 SHA256 为 `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf`。原平面镜像指针与头入口支持本轮使用的 `0xffffffc001000000` 基址；它不是 ELF。本轮没有把其他设备的装载布局套到该文件。

## 矩阵已与 Sony 的 VENICE 输入变换对应

恢复矩阵为：

```text
 1.151840210  -0.117706299  -0.034133911
-0.040527344   1.206619263  -0.166091919
-0.012313843   0.007247925   1.005065918
```

将 Sony 提交的 VENICE S-Gamut3→ACES AP0 矩阵与 Academy 的 AP0→AP1 变换组合，九个系数四舍五入到 Q16 后，**全部与固件整数相同**。最大未取整差为 0.42256 个 Q16 单位。普通 Sony S-Gamut3 输入矩阵作为反对照，最大差约 5566.71 个单位。它支持此处使用了 VENICE 输入变换的数学，而非只依据名称推断。

原初始化代码实际引用 `MLUT_MTX_A_REG_SG3TOAP1_0`；它与带 VENICE 名称的矩阵记录逐字节相同。不能只数 VENICE 名称引用而遗漏这个别名。相关原数据位置：VENICE 命名矩阵 `0xc15b78`，实际被复制的等值矩阵 `0xc15aa8`。

来源：[Sony 提供的 VENICE IDT](https://github.com/aces-aswf/aces-core/blob/v1.3/transforms/ctl/idt/vendorSupplied/sony/IDT.Sony.Venice_SLog3_SGamut3.ctl)、[普通 Sony IDT](https://raw.githubusercontent.com/ampas/aces-dev/v1.3/transforms/ctl/idt/vendorSupplied/sony/IDT.Sony.SLog3_SGamut3.ctl)、[Academy AP0/AP1 定义](https://raw.githubusercontent.com/aces-aswf/aces-core/v1.3/transforms/ctl/lib/ACESlib.Utilities_Color.ctl)。VENICE 原文通过 GitHub contents API 读取，blob `a464ffa21b03ae09b7442a872e315f33457f4a10`。后续可选刷新遭 API 限额，保留访问缺口；比较脚本使用本轮已经核读的原始数值离线重现，不伪称三份源码均已另行下载校验。

这仍不说明 FX3 的传感器前端与 VENICE 相同，也不确定前面是否已经做过输入归一化。后续须追上游数据域，不能在现有画面上再次无条件乘同一矩阵。

## 3D 存储布局已逐值复核

每通道八个 bank，每个 bank 有 500 个 32 位字，即 1000 个 16 位值。整体正好是 20³ 节点。解交错规则：

```text
bank = ((r & 1) << 2) | ((g & 1) << 1) | (b & 1)
index_in_bank = (r // 2) * 100 + (g // 2) * 10 + b // 2
```

在独立的原厂 THRU 表上，所有输出分别精确等于对应 R/G/B 轴值。VENICE 表的三个通道输出均在 0–8192，配置中提取的 20 个候选轴值为 0–6209。**尚未恢复全部定标、1D 采样位置和硬件插值器，因此只交付原整数网格，没有把猜测归一化后的文件命名成可直接导入相机的 `.cube`。**

数据：[矩阵 CSV](tables/venice_matrix_signed_q16.csv)、[1D 槽 CSV](tables/venice_1d_packed_halfwords.csv)、[20³ 整数网格](tables/venice_3d_20x20x20_raw.csv)。30 份原始小表与各自摘要也已保留，未分发完整固件。

## 已追到实际配置与控制代码

原配置查询函数 `av-cam+0x2c3334` 返回：

```text
look ID:       22
name:          MLUT_LOOKNAME_SL3SG3_TO_ACESREC709
descriptor VA: 0xffffffc001b05638
count:         70
```

这组配置的后半段包括 YC→RGB、S-Log3→线性、上述 SG3→AP1 矩阵、VENICE 1D、20³ 3D、Full→Legal 与 RGB→YC709 记录。这里的命名是 **ACES Rec.709 外观处理配置**，不能当作完整 VENICE CMOS/ISP。它的具体记录与顺序可由初始化结果复原。

- 原初始化入口：`0x2baf00`、`0x2bc100`、`0x2bc330`；执行 64,082 条 guest 指令、1342 次原始 memcpy，寄存器和栈恢复一致。原始 memcpy 位于 `0xd80`，未以自写 memcpy 替代。
- 原装载列表生产函数：`0x2c4794`；它读取每项的 `+0` 源指针、`+8` 寄存器偏移、`+0x10` word count，按 0x98 字节步长消费记录，写出 16 字节 DMA 项。
- CPU guest 中使用明确声明的地址转换和 cache 回调。IP=0 得到寄存器低32位基址 `0xf3019000`；每个有效案例 209 次转换、70 次 cache 回调。地址映射增加 64 的反对照仅改变相应源/next 地址。
- IP=1 直接调用列表生产者会产生零寄存器基址；该案例是**反例**，不算有效硬件配置。上层设置前端本身拒绝 IP=1。原列表函数没有独立保证所有输入合法。
- 原设置前端：`0x2b5ffc`。IP=0/look=22 到达队列入口 `0x2c4cc8` 前，已形成 72 字节参数、look=22、事件字段 `0x02ae085a`。本轮在入口前停下，没有声称排队、DMA 完成或回调成功。

上述是分开的受限实验，不是一条已经在相机上跑通的端到端录像链。装载边界后还有同步、DMA 提交、中断/回调、实际视频分支和参数寿命待核。

## 实现方向与下一处要追的缺口

本轮将“有几个字符串”推进为“有真实表、正确布局、数值来源、内置配置、原始控制前端及装载列表生产代码”。FX3 原生框架已经包含这段 VENICE/ACES 数学及相应装载机制，接下来应沿这些代码适配具体功能。

下一处决定实现成败的工作是：追 FX3 正常拍摄控制怎样到达该 MLUT 后端，确认哪条 MAIN、监看、代理或 HDMI 分支使用它；恢复一维曲线的坐标/尺度和 3D 硬件插值，再用固定输入验证原始输出。之后才能在原 UI 属性模型中暴露或改造对应设置。没有用“FX5 完整包没发布”替代这些可以做的工作。

FX5 完整包、VENICE type4 内层仍是取得更多专有算法的独立分支。本轮查阅了 fwtool 维护者的格式说明并检索 type4/产品名，没有找到可直接处理本地 VENICE 内层的已核验实现；未识别出其密码算法或密钥。该分支暂未新增解密结果，不据此断言不能研究或不能实现。

## 复现与文件

全部脚本仅访问本机镜像和自身输出；使用已有 Python 环境，无新虚拟机、相机连接或刷写。

```sh
python3 work/fx3-color-port-20261027/extract_color_tables.py
python3 work/fx3-color-port-20261027/compare_aces_matrix.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/run_profile_initializer.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/run_look_consumer.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/run_control_boundary.py
```

对应回执：[提取](extraction-results.json)、[公开矩阵对照](aces-matrix-comparison.json)、[原初始化](initializer-guest-results.json)、[原查询与 DMA 列表](look-consumer-guest-results.json)、[控制入口](control-boundary-guest-results.json)。静态候选 xref 扫描含启发式假阳性，只有本页指出且经指令/guest 核对的函数用于结论。

本轮未修改原始镜像、H.265 实现、旧 stage、GOAL、VENICE 工作树或相机数据。此处是离线逆向与受限原指令验证成果，尚无已刷入文件或真实成片验收。
