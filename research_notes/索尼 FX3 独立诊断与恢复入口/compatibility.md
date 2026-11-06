# Assigned topic

经典 ILME-FX3 与 FX3A 的诊断兼容性、独立恢复入口证据。核验日期：2026-10-25。仅公开维护者仓库、问题原帖和 Sony 官方页面；未下载诊断附件，未运行工具，未访问相机接口或操作 Windows。

## Key question 1：经典 ILME-FX3 7.02 是否已有完整成功记录？

### Takeaway

本轮未找到同时明确「经典 ILME-FX3 + 7.02 + 工具提交 + 服务认证 / 完整回读 / 独立救援结果」的可复核记录。确有旧经典 FX3 服务设置解锁报告，也确有 FX3A 2.02 的新成功记录；不能合并成经典 FX3 7.02 已验证。

### Cited Findings

| 来源 / 日期 | 精确对象 | 原帖实际完成的范围 | 尚未证明 |
|---|---|---|---|
| [PMCA #504](https://github.com/ma1co/Sony-PMCA-RE/issues/504)，2024-04-02 | 标题和正文称日版 FX3 / FX30；FX3 固件及代码 SHA 未披露 | 作者称 Linux ARM 虚拟机中 serviceshell 后语言解锁；评论提到 35 种语言 | 不足以定位经典 FX3 固件，不是完整固件回读或恢复记录 |
| [PR #714](https://github.com/ma1co/Sony-PMCA-RE/pull/714)，2026-05-25 起 | 最初测试为 A7RV / A7SIII；2026-10-13 留言为经典 FX3 J1、6.2（原文写法） | 初始 PAL/NTSC 属性修改；FX3 留言明确尚未尝试，只在求证 | 经典 FX3 6.2 或 7.02 成功均不能由该留言推出 |
| [REA #3027](https://github.com/morluto/rea/discussions/3027)，2026-10-13 | FX3 7.02 | 请求研究电池限制 / homebrew，页面 0 条评论 | 不是已有解密、补丁、刷写或救援成果 |

### Inferences

- 应把“经典 FX3 7.02 未验证”写成证据缺口，而非“经典 FX3 无法使用任何服务功能”。
- 识别 MSC 设备、完成服务模式认证、读到某个设置、完整分区回读、写后可独立恢复是不同结果，前一个结果不能替代后一个。

### Gaps

- 当前真实设备仅有父任务提供的缓存 MSC 盘点：ILME-FX3、054C:0DA1、Microsoft USBSTOR、状态 OK；固件数字仍待用户实机核对，研究暂按 Sony 7.02。
- 尚缺经典 FX3 对应固件、工具 SHA、接口/驱动、原始认证记录、只读命令范围、回读哈希和恢复前后验收成套证据。
- 检索覆盖 PMCA #504 / #524 / #715、PR #714、REA #3027、README 与 FX3+7.02 / serviceshell / bootrom 定向检索；未找到不等于已证明全球不存在。

## Key question 2：#715 真正结案原因是什么，能否支持当前服务入口？

### Takeaway

#715 不能再作为“FX3A 服务协议不支持”的失败证据：同一作者在 2026-06-09 报告成功并关闭问题。它仍不证明经典 FX3 7.02，更不证明 updatershell 或救砖可用。

### Cited Findings

- [#715 完整线程](https://github.com/ma1co/Sony-PMCA-RE/issues/715)：最初 FX3A 在 M2 / macOS 环境已被 MSC 识别，但切换服务时 USB 超时；updatershell 则独立报该型号不支持自定义更新。尝试检测 PR698 后仍超时。
- 同帖 6 月 9 日成功范围：FX3A **2.02**，macOS Tahoe / M2，Homebrew libusb、Conda Python **3.11**，以管理员进程显式传递动态库路径后服务认证成功，切到 PAL，25p/50p 出现。作者称重启保留、相机 reset 后不保留；没有提供测试代码 SHA。[成功结案原帖](https://github.com/ma1co/Sony-PMCA-RE/issues/715)
- 7 月 7 日补充只是语言解锁项可见、31/35 显示；作者明确未实际施加语言解锁。不能计为该项成功。[同一线程](https://github.com/ma1co/Sony-PMCA-RE/issues/715)
- [固定 README](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/README.md) 将 updater 路径与 senser 服务路径分开；CXD90045 / CXD90057 因固件签名不能走该自定义 updater 路线；服务模式针对运行中的系统。本文未凭外观或传感器给 FX3 / FX3A 指派已核验的处理器子型号。
- [PR714](https://github.com/ma1co/Sony-PMCA-RE/pull/714) 中另一台 A7IV 6.0.2 有设置读写成功、文件 pull / bootrom 失败的报告。这只是操作范围可分裂的异机实例，不是 FX3 结果。

### Inferences

- 超时可能位于主机动态库、模式切换重枚举或认证链，#715 后续成功已排除其最初“该型号必然协议不兼容”的推断；但没有完整抓包来断定唯一根因。
- 服务认证成功依赖运行系统，不能当作主系统损坏后仍可进入的独立恢复通道。
- 本轮仅固定当前公开代码供后续审计：PMCA master 为 `a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`；PR714 head 为 `3c6646e6c72e29568fc491d179050a86c392f22c`。这是 2026-10-25 的远端引用，不是成功报告当时的运行 SHA。

### Gaps

- #715 没有经典 FX3、7.02、完整固件 dump、写回或砖机救援记录。
- 新 Rust 重写工具 [PMCA-RE Reloaded README](https://github.com/masterflai/pmca-re-reloaded/blob/d4bcaef29191a44b290ff23c3290f8551c8303fa/README.md) 仍称官方固件刷写未在相机实测；macOS 26 暂仅 MTP 信息读取，服务功能待修。它描述的设置备份与回读保护是设计说明，不是 FX3 7.02 的实机恢复验收。不能因 GUI 或自动驱动就升级兼容性结论。

## Key question 3：是否存在 FX3 专属 BootROM / UART / eMMC 救援，或官方同版本强制重刷？

### Takeaway

本轮没有找到 FX3 专属、可复核的底层恢复闭环。已存在的是 A7IV 的研究实现与 Sony FX3 特定更新失败排查流程，适用边界不同。

### Cited Findings

- [A7IV 固定 README](https://github.com/DavidBuchanan314/ILCE-7M4-RE/blob/2328d18ce640e6c8cd9341efcf0043ce9042a135/README.md) 明确对象为 ILCE-7M4：作者实现串口 BootROM 入口、裸机 fastboot payload、eMMC 分区 USB 备份/恢复；**boot0 的 dump/flash 加解密尚未实现**。这是 A7IV 的实现声明，不是 FX3 移植或 FX3 救援报告。
- [Sony FX3 7.02 官方页](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)，发布 2026-03-17，适用 ILME-FX3：通过相机菜单触发卡内 BODYDATA.DAT 更新；已有 7.02 时称无需更新。失败章节针对目标型号错误或指定灯码，建议重新准备卡并重试；没有提供同版本强刷开关或无需主菜单的通用恢复入口。

### Inferences

- A7IV 代码要成为 FX3 救援工具，至少需验证 FX3 具体 SoC / BootROM 版本、串口电气与引脚、复位时序、RAM 与控制器地址、payload、eMMC 分区布局、密钥及 boot0 处理，再有独立的备份/恢复实机闭环。共享 BIONZ XR 名称不足以替代这些证据。
- “Sony 说明已有最新版无需更新”不等于数学上证明同版本绝对不能写入；准确结论是公开消费者文档没有给出受支持的同版本强刷/强制恢复方法。
- 指定的升级错误可重试，不等于引导区损坏、系统无菜单或硬件故障均可由换卡解决。

### Gaps

1. 先寻找经典 FX3 7.02 的精确服务入口报告、固定 SHA 和只读范围；不为填证据缺口直接试主机驱动或切服务模式。
2. 如做离线源码审计，优先找独立入口与退出条件、只读协议是否暗含写入、可否读全启动相关分区及校准/NVM，而不是先寻找一个 H.265 开关。
3. 需要受损系统仍能进入的 FX3 独立恢复证据、可用的同机原始数据和确证的返修路线；当前不能承诺“变砖能在现有 Mac / Windows 救回”。
