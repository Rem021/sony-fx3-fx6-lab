# Sony 现代固件逆向项目与 REA 的真实边界

## REA 是什么，能否把研究直接变成安全刷机？

### Takeaway
用户已确认“逆向一切”指 REA（Reverse Engineer Anything）。它能编排离线分析工具、辅助解释二进制；没有公开证据证明它能自动完成 FX3 1080p HEVC 开发、签名／启动验证、救砖和长期验收。

### Cited Findings
- REA 官方将它定义为连接智能体与 Hopper/Ghidra/IDA 等分析器的 MCP；不是某款 Sony 的第三方固件。固定研究版本 `fead4fdaa7410ed2f7421fbce37e546c9cd6d7e4`，提交时间 2026-10-25 05:47:41 UTC（洛杉矶仍为 10-24）。[官方仓库](https://github.com/morluto/rea/tree/fead4fdaa7410ed2f7421fbce37e546c9cd6d7e4)
- 固件模块使用 Binwalk 3.1.x 检视、Unblob 26.6.x 提取，再将提取出的 ELF 单独交给 Ghidra；第一阶段只验证 Linux x64。文档特别区分覆盖率意义的 complete 与“完整重建固件”，并保留未知、加密、提取失败区域。[固定版固件分析说明](https://github.com/morluto/rea/blob/fead4fdaa7410ed2f7421fbce37e546c9cd6d7e4/docs/firmware-analysis.md)
- 2026-10-13，REA 仓库 FX3 Discussion #3027 是用户请求移除第三方电池限制，提到 7.02；本次公开页面仍为 0 回复。它是需求单，不是已破解成果。[原始讨论](https://github.com/morluto/rea/discussions/3027)
- 对下文四个关键项目固定 SHA 的 README 文本检查，均未发现 REA、morluto 或 Reverse Engineer Anything；MDHan 仅提到可让 Codex／Claude Code 协助操作。因此不能把社区 Sony 成果统称为“REA 已实现”。[QAQLeonard README](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/README.zh-CN.md)、[YuuLuo README](https://github.com/YuuLuo/a7c2-service-preload/blob/1619f938663a36d41e72302a8cfee89a0f6acd1a/README.md)、[MDHan README](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/README.md)、[leogenot README](https://github.com/leogenot/sony-a7iv-feature-research/blob/12582457829e34eae7211df5b0c599fa46b7e5e1/README.md)

### Inferences
- REA 有助于检索功能门控、产品类、编码参数和调用关系。缺少密钥／解析器时仍需 Sony 专用工具；发现模式名称或字符串也不能证明录像链路存在。
- Linux x64 验证边界不意味着完全不能在 Mac 用 REA；只是本次不能承诺其固件模块已通过 macOS 验证。可先使用已支持 FX3 的专用离线解包器，再选适用的静态分析器。

### Gaps
- 未发现 REA 官方展示的 FX3 新编码补丁、ZV-E1 跨刷 FX3 成功案例，或任何相关可重复验收／恢复记录。
- README 检查只涵盖上述文件，不能证明整个项目从未借助 REA；本次不对开发者未公开的工具使用做推断。

## FX3 现在到底能否离线解包，旧 OpenMemories 还有什么意义？

### Takeaway
截至本次核查，现代 FX3 解包已有维护者公开证据。不能再简单说“BIONZ XR 加密所以完全拆不开”；但解包、运行代码、修改文件、签名更新、启动与恢复是不同层次。

### Cited Findings
- `ma1co/fwtool.py` 的 PR #52 于 2026-09-10 提出 CXD90057 支持，DavidBuchanan314 的已测试列表明确包含 ILME-FX3、FX6、FX2、A7C II、A7S III 等。PR 仍 Open，主仓库 README 仅列旧平台，查看主分支会漏掉本轮进展。FX3 具体已测固件版本未在列表旁逐一给出。[维护者原始 PR](https://github.com/ma1co/fwtool.py/pull/52)
- 研究分支固定为 `DavidBuchanan314/fwtool.py:a7iv`，SHA `3955d7890fc38daf942bb52827599bfe35de4a14`，2026-10-09 16:13:06 UTC；这是应纳入后续离线实验的候选，不等于本次已下载 FX3 7.02 实测解包。[固定分支源码](https://github.com/DavidBuchanan314/fwtool.py/tree/3955d7890fc38daf942bb52827599bfe35de4a14)
- `Sony-PMCA-RE` 将应用安装、更新器执行和服务模式分开。传统 updater 模式利用次要分区执行自定义代码，主固件保持未修改；它说明 CXD90045/90057 的加密签名使该旧方法不兼容。服务模式是另一条通信和执行路径。[官方项目 README](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/README.md)
- OpenMemories Tweak 的范围是支持 PlayMemories Camera Apps 的机型、既存隐藏设置（语言、时限等）；该 Android 应用不是 FX3/ZV-E1 可用的通用固件。[项目 README](https://github.com/ma1co/OpenMemories-Tweak)
- q19032 的独立解包研究解释了 CXD90057/58 等平台的密钥推导思路，未提供本次目标编码模式的补丁。研究快照 `e118ab0145275382d6114e047b8ce4df98020374`，2026-09-12 11:25:26 UTC。[原始研究](https://github.com/q19032/Sony-firmware-unpacker/tree/e118ab0145275382d6114e047b8ce4df98020374)

### Inferences
- 解密密钥解决保密性，不能自动伪造签名；能解包与能让修改镜像被原厂更新器接受不是一回事。
- FX3 7.02 离线解包是合理下一步，且不需要连接相机。必须记录官方下载地址、尺寸／SHA-256、工具版本、提取日志与主要 ELF，不把维护者兼容声明伪装为本机实验成功。

### Gaps
- 本子任务未执行解包，未运行任何下载工具，未连接或写入相机；没有 FX3 7.02 的实测提取清单。
- 未核定 FX3 当前启动验证覆盖范围、签名接受路径或可独立恢复的服务／BootROM 方案。不能用旧 PMCA 说明断言所有现代路径已被永久封死，也不能宣称已普遍解除保护。

## 网上 A7C II 新功能究竟是宣传，还是已有局部移植？

### Takeaway
真实局部移植已经出现，且有公开源代码与版本约束；不能用 2025 年 CAMSET.DAT 猜测项目否定 2026 年的新成果。当前成果主要是限定机型／固件的本机补丁，不能拿来直接刷 FX3 或 ZV-E1。

### Cited Findings
- 较早 `jpaulrez/sony-a7c2-hacks`（SHA `378b060605ddaf2212a0d63524052b9cb1496a3c`，2025-06-03）研究 2.00 导出 CAMSET*.DAT 和可能的 4K60 全幅／LUT；其 README 与目录是实验资料，不能当成 4K60 全幅已实现的证据。[该历史项目](https://github.com/jpaulrez/sony-a7c2-hacks/tree/378b060605ddaf2212a0d63524052b9cb1496a3c)
- 新 `QAQLeonard/a7c2-fl23-research` 只支持 ILCE-7CM2 2.01，功能包括 FL2/FL3、自定义外观、快门声、竖屏。验证表较标题窄：作者 Windows＋一台相机通过 FL2/FL3、六外观、恢复、预览拍照；持久声音长期验收中、竖屏重写待验、该 GUI 的 Mac USB 未验。README 明示写入读回不证明启动安全，恢复不保证救砖。[固定 README](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/README.zh-CN.md)
- 该仓库 HEAD 研究快照 `9f69e9dc59ef2cfbc3334bee977b7529aaee04b8`，2026-10-25 05:42:18 UTC；最新发布 v3.0.3，tag 提交 `782785641ca9f8b984940c7274b48706219e0da4`，发布时间 2026-10-23 04:59:59 UTC。版本说明包含 USB 收包错误、旧基础外观不同步和中断续接等实际修复，不应脱离版本谈可靠性。[v3.0.3 发布](https://github.com/QAQLeonard/a7c2-fl23-research/releases/tag/v3.0.3)
- 源码不只是改菜单设置：`core.py` 以原版整文件哈希、机型／2.01 与固定窗口校验 `appFw.so`/`cpapp-b.bin`；installer 固定写 `/usr/lib/appFw.so` 与 `/cp/cpapp-b.bin` 文件窗口并 fsync，属于本机程序持久修改。manifest 明确普通签名存储卡 updater 不是该流程，并列一机身验收范围。[core.py](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/core.py)、[installer.c](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/native/installer.c)、[manifest](https://github.com/QAQLeonard/a7c2-fl23-research/blob/9f69e9dc59ef2cfbc3334bee977b7529aaee04b8/src/fl23/assets/manifest.json)
- YuuLuo 服务入口研究，SHA `1619f938663a36d41e72302a8cfee89a0f6acd1a`，2026-10-15：在 A7C II 2.01 观察到服务认证＋Jiritsu 路径越界＋preload 导致 root 子进程临时代码执行。作者明确这不永久禁用签名，安装修改固件仍需独立接受路径。[固定 README](https://github.com/YuuLuo/a7c2-service-preload/blob/1619f938663a36d41e72302a8cfee89a0f6acd1a/README.md)
- 独立 Mac 适配 MDHan 0.2.3，SHA `41950d3eab53e0b801f315af07505a2d0d3f76af`，2026-10-21。README 的“添加 FL2/FL3”和“恢复”需与验证表同时读：有限机身反馈，原始首次安装中断仍有记录，实际恢复未测。2026-10-21 新用户重试后的工具验证通过，不等于人工拍摄／回放全部完成。[固定 README](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/README.md)、[详细验证边界](https://github.com/MDHan/a7c2-fl23-macos/blob/41950d3eab53e0b801f315af07505a2d0d3f76af/docs/VALIDATION.md)

### Inferences
- 技术上，Sony 的某些新功能确能通过本机代码／参数移植；但限定源码的固定偏移、整文件哈希和机型检查恰恰说明不能跨机型套用。
- 固定文件写入不是原始全闪存覆盖，仍会影响启动和运行；“无整包刷机”不能等同“无变砖风险”。
- 上游和独立 Mac 适配对供体彩色数据、阶段与验证状态存在版本差异，报告避免笼统宣称“完全等同 α1 II 色彩”或“Mac 已全面实测”。

### Gaps
- 本次没有独立实机复现，未下载私有机身备份、未检查原创样片像素或原始全日志；上述硬件结果是维护者／用户报告的证据等级。
- 未找到这些 A7CII 项目支持 FX3、ZV-E1 或 1080p HEVC 编码模式的声明。

## 快门角度、语言解锁能否证明 FX3 编码或 ZV-E1 跨刷可行？

### Takeaway
不能。持久设置、图标显示、真正可调功能、全链录像与跨系统移植必须分别验证。本次没有找到可重复的 FX3 1080p29.97/30 HEVC 主录补丁。

### Cited Findings
- `leogenot/sony-a7iv-feature-research`，SHA `12582457829e34eae7211df5b0c599fa46b7e5e1`（提交时间 2026-09-21）：A7IV 6.02 的快门角度只确认图标显示，拨轮／触摸调整仍门控；LUT 代码存在但产品类排除，修改备份设置仍不出现菜单。Open Gate／DCI 代码同样没有证实编码／产品路径。[原作者验证表](https://github.com/leogenot/sony-a7iv-feature-research/blob/12582457829e34eae7211df5b0c599fa46b7e5e1/README.md)
- SonyAlphaRumors 2026-10-22 发布读者称 A7SIII 5.01 开启角度的消息。这不是原始可重复实验记录；本研究不把该媒体来信升级成完整功能验收，也不以其“共用程序”推导整系统兼容。[媒体原文，仅用于追踪线索](https://www.sonyalpharumors.com/new-shutter-angle-hack-works-on-the-sony-a7siii-too/)
- ZV-E1 的公开教程聚焦服务模式语言设置，明确不刷固件；来源是 PMCA issue 的用户经验，未逐一绑定当前固件版本。研究 SHA `b0f96aea69a34cb7a8647104d614841a3c246fc5`，2026-05-23。[教程及引用链](https://github.com/optiplex331/sony-zv-e1-english-menu-unlock/tree/b0f96aea69a34cb7a8647104d614841a3c246fc5)
- SonShell 使用 Sony Camera Remote SDK 控制相机与同步文件，虽然标题借用了“ssh into camera”，不能当成 FX3/ZV-E1 root shell 或第三方固件证据。[项目原始说明](https://github.com/goudvuur/sonshell)

### Inferences
- 用户所需 FX3 HD HEVC 更值得先查已有编码链与分辨率／帧率配置，风险和工作量通常小于跨刷全部系统；这只是研究优先级，不是可实现结论。
- 安全论证至少需精确机型／固件匹配、源码和可再生补丁、原版／目标哈希、启动和长录样片、媒体探测、温度／掉电行为、更新行为与真实恢复路径。目前这些没有针对目标形成闭环。
- 即便共享程序中含 FX3 产品类和相关菜单，也可能依赖特定硬件、产品路由和驱动；换产品标识不等于可工作的电影机系统。

### Gaps
- 本次检索未发现 FX3 1080p29.97/30 HEVC 主录的公开 patch、对应版本、原始样片与恢复记录；结论是“未找到可核验实现”，不是数学证明不可能。
- 本次未找到 ZV-E1 刷完整 FX3 系统的公开复现。本子任务只核验公开项目；具体硬件与官方升级限制由另一研究分支覆盖。
- 用户说 FX3“最新”，不是机身读取证据；任何未来针对性分析仍需型号后缀、实际版本和地区模式，不能据网页最新号直接推断机身状态。
