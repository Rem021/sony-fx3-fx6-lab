# FX3 色彩控制链与新增选择适配原型

本轮承接上一轮真实色彩表提取，继续执行原始代码和实现适配。**已做出离线控制适配原型 V2：新增显式请求经 CP 选择 ID 22，同时修复采集参数检查对新增值的归零。** 30 种适用消息形状通过组合实验；现有 512 组 CP 消息案例不变，参数检查的 256 个字节输入中只有新增值 12 改变。

此成果是控制层原型，尚未接入机身菜单、真实 IPC 或实际主录像素。本轮没有修改相机、H.265 工具、旧阶段和其他工作树。上一轮 [数据与装载实验](../README.md)及封存回执保留。

## 从应用模型追到 CP 原生外观选择

原 `appFw.so` 中的 `set_base_picture_setting_i` 位于 VA `0x2e26fcc`。函数的原签名列出 LUT 选择、用户表是否存在、Log 设置、输入信号、色域、Picture Profile 和拍摄模式七个模型参数。它在消息 `+8..+12` 写五个字节。

本轮执行原 AArch64 函数的 **5120 组声明输入**，得到 64 种不同五字节结果；随后调用原 CP Thumb 接收函数 `file+0x689f9c`，确认依次展开到：

| 消息字段 | CP 设置域 | 原日志给出的名称 |
|---|---|---|
| +8 | +0xba0 | base_look |
| +9 | +0xba4 | shooting_mode |
| +0xa | +0xba8 | input_gamut |
| +0xb | +0xbac | color_gamut |
| +0xc | +0xbb0 | target_display |

接收函数还增加 `+0x76c` 的变更计数。`shooting_mode=3` 时，它保留旧 `color_gamut`；不能把消息字节都当成无条件覆盖。512 组 CP 案例覆盖了两种旧色域和两个仍未定名的条件字段。

原 CP 基础外观转换 `file+0x8d1ad6` 再进入 `GetVfxMlutLookname`，后者在 `file+0x3266ec`。768 组独立选择案例与应用生成的消息域都没有自然选出 ID 22。原函数另有一个运行时覆盖字节，声明置 22 时可返回 22；本轮仅在 guest 内测试，未把该字节当成可直接操作机身的功能开关。

这里是将原函数按明确参数合同分别调用的组合验证；没有实际发送跨处理器消息，也没有取得当前场景或机身 RAM。

## CP 的实际后端已与上一轮数据对应

独立读取 CP 自己的配置注册表后，ID 22 对应：

```text
MLUT_LOOKNAME_SL3SG3_TO_ACESREC709
70 项配置；CP 初始化目标地址 0x02015794
```

本轮执行 CP 原 Thumb 初始化函数 `file+0x911650..0x9169b8`，并执行同镜像的原 ARM memcpy。共 64,546 条 guest 指令、1166 次复制，栈和被调用者保存寄存器保持。

将其 ID 22 的全部 70 项按顺序与上一轮 AArch64 配置比较：名称、寄存器偏移及长度均相同；**67 项文件内载荷逐字节相同**，包括真实矩阵、曲线和三维表。其余三个选择值指向 CP 运行时 RAM `0x13e624c/50/54`，没有拿声明零值冒充原件数据。

因此前一轮恢复的 VENICE／ACES 数学也确实存在于正常 CP 图像控制后端，编号不只依赖另一份镜像的猜测。完整 sensor/ISP 同源性仍未由此证明。

## 原异步状态与回调已核对

原 CP `SetVfxMlutParam`、状态判断和 `MlutLookNameCallback` 在 guest 中执行，驱动 API 返回值明确作为声明输入：

| 阶段 | state | look | pending | 判断 |
|---|---:|---:|---:|---|
| 准备 API 返回 0 后 | 1 | 0 | 0 | 尚未设置外观 |
| 设置 API 返回 0 后 | 2 | 22 | 1 | 等待回调，未就绪 |
| 忙碌中再次调用 | 2 | 22 | 1 | 不重复发起设置 |
| 原成功回调执行后 | 2 | 22 | 0 | 原就绪判断成立 |
| 准备／设置／回调错误 | 0 | 0 | 0 | 回到未就绪状态 |

这些测试证明原控制代码在给定 API 结果下的行为；没有证明实际驱动完成、硬件导致回调或真实帧应用。

## 新增适配原型与遇到的第二道限制

原型使用一个新的**显式适配请求**，在适用的消息域中把 CP `base_look` 设为此前普通路径未使用的 12；一个 16 字节 Thumb 分派片段把该值映射到现有外观 ID 22，其余值继续调用原选择函数。它没有占用已有 `Select LUT` 模型的编号 12 或用户表槽位。

初版通过了 VFX 选择测试，继续追查后发现 `file+0x1cb8a8` 处还有范围检查：`base_look >= 12` 会记录错误并将输出字段 `+0x794` 归零。初版选择成功不能代表该参数已通过后续处理。

V2 在隔离 guest 中将这处 `cmp r1,#12` 改为 `cmp r1,#13`，只增加值 12；其他原合法值和 13–255 的拒绝行为保持。组合结果为：

- 512 组既有 CP 消息经过分派片段后，与原函数结果完全一致。
- 原范围检查与候选检查各测 256 个输入，只有 12 的结果改变。
- 30 种符合原型限制的消息形状选择到 CP ID 22，并在此参数构建阶段保留新增值 12。
- 其余 34 种消息形状由原型拒绝；特别是拍摄模式会强制其他外观的分支和未纳入的色域条件。

**域名纠正：这里的 EC 属于 `Camera::EC` 相机曝光／采集控制，不能解释为 Encoder。** 原件还包含 `EC_CaptureRaw_CalcAe.cpp`、`EC_GetExtInfo.cpp`、`EC_SetExtInfo.cpp` 等直接证据。早期代码文件名 `encoder_parameter_gate.py` 保留作兼容，新入口为 `capture_parameter_gate.py`；旧文件名不作为编码器或主录归属的证据。

16 字节分派片段只运行在声明的 guest 地址。两字节检查改动只写入 guest 内存；未修改完整固件，也没有确定机身可放置代码的位置、启动／签名处理或菜单接入。

## 监看控制已分出，但 MAIN 归属仍未完成

另追到应用的 `infra_wrapper_bb::detail::vdf_disp_set_monitor_lut`，原函数 VA `0x2debdb0`。五个输入枚举在传输入口前分别生成监看命令，目标消息 ID `0x92840747`，请求头 `200d/0161/000a/8001`。本轮在传输前停止。

这与 CP 的 Base Picture Setting 消息是两条具体可辨的控制路径。Sony 官方也分别定义了 [Display LUT 监看](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888936.html)和 [PPLUT 录制应用](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000876510.html)。它们帮助核对功能边界，不能替代当前机身输出验证。

本轮还定位到采集参数调用者 `file+0x1c36d0`：仅当对象 `+8` 的类型值命中 `0x32207` 位掩码时调用上述字段构建函数，对应数值 `[0,1,2,9,13,16,17]`。这些类型与 MAIN、代理、监看、静态采集的具体对应仍未恢复，不能给它们随意命名。

## 下一处实现缺口

已实现的新增选择适配原型可以复现“消息字段→原选择函数→ID 22→采集字段检查”的控制行为。继续工作应集中在：

1. 从调用者追类型字节 `+8` 的生产者，再追输出 `+0x794` 的实际消费者，确认视频支路与处理顺序。
2. 审查更早的模型／IPC 接收条件，给新请求安排明确的属性和菜单，而不是覆盖原用户 LUT 项。
3. 恢复三个 RAM 选择值、实际资源归属，以及一维坐标和三维硬件插值合同。
4. 在真实输入／输出上核对像素、主录与监看差异，再讨论部署。完整 RAW、AWB、去马赛克及降噪链还未由这个原型实现。

## 复现与回执

使用原有 Python 环境，在 Mac 项目根运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/route-20261028/cp_look_route.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/route-20261028/ap_cp_message.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/route-20261028/cp_profile_backend.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/route-20261028/cp_async_control.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/route-20261028/monitor_boundary.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/route-20261028/candidate_adapter.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/route-20261028/capture_parameter_gate.py
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-color-port-20261027/route-20261028/candidate_adapter_v2.py
```

主要回执：[应用→CP](ap-cp-message-results.json)、[CP 配置原件比较](cp-profile-backend-results.json)、[异步状态](cp-async-control-results.json)、[监看命令](monitor-boundary-results.json)、[范围检查](capture-parameter-gate-results.json)、[适配原型 V2](candidate-adapter-v2-results.json)。本目录只含离线分析、代码和回执，无相机或 USB 操作。
