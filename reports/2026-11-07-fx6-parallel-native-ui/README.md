# FX6 原生菜单并行研究：版本纠正与下一处观测点

2026-11-07。本轮基于 Orca 的实时 agent 状态与现有候选，完成三个独立研究任务，并补充整包成员核验。没有启动或控制 VM、修改运行候选或操作相机。研究启动时 DeepSeek 正在运行 Candidate 287，Antigravity 正在修正界面路线；本轮不占用其运行窗口。

## 确定结果

**原有三屏不能作为 FX6 原厂菜单成功的证据。** 网页的 `/frame.png` 来自宿主 Pillow 绘制；报告 10.7 的 `scr7286_0001` / `rep_shooting` / `rep_menu` 地址来自 FX3 的 79 MB `appFw.so`，不是当前 FX6 的 50.5 MB 文件。已找到真实 FX6 的三个 presenter 构造入口和 489 条有效控件描述符，供原厂启动链继续定位。

| 已核实项目 | 结果与影响 | 可复核材料 |
|---|---|---|
| 文件身份 | FX6 `50,520,424 B / a1c58b69…`；FX3 `79,015,712 B / 545c5053…`。FX3 owning manifest 的 `files[17]` 明确绑定后者 | [资源与控件复核](native-resources/REPORT.md) |
| 真 FX6 Big6 | `procam_big6_menu_home_presenter` 构造 `+0xde10f4`，表 `+0x2e9e210`，98 项 | [结构化指纹](native-resources/audit-result.json) |
| 真 FX6 拍摄界面 | `procam_shooting_presenter` 构造 `+0xdd3df8`，表 `+0x2e94910`，356 项 | 同上 |
| 真 FX6 菜单首层 | `procam_menu_layer_1st_presenter` 构造 `+0xdd7470`，表 `+0x2ea02f8`，35 项 | 同上 |
| UI 初始化 | `Application_System_Init +0xc0b044` 返回不代表 `UI_worker +0xc0b470` 已进入；OSAL 存在负返回后不执行回调的路径，尚无本次失败返回或 errno 证明根因 | [初始化链复核](native-init/README.md) |
| 已结束运行 | 273/280/283/286 的采样 gpe0 均全零；286 有入口 dlsym 失败；280 有可归属 appFw 的未对齐线程入口异常；通用 busybox SEGV 另列 | [运行与显示链复核](runtime-evidence/README.md) |
| 网页显示/输入 | 无 VM 帧读回，页面切换只改宿主 state，按键缺少 native ACK / 模型确认，TCP1234 与所选 Unix GDB socket 不一致 | 同上 |

以上地址只适用于 SHA-256 为 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067` 的 FX6 donor，运行时加真实模块基址。构造入口需要已有应用上下文，不能当作无参 `open_screen()` 调用；本轮没有证明原生屏幕已打开，也未从这些表推导坐标。

## Candidate 成员绑定复核

[inspect_cpio_binding.py](inspect_cpio_binding.py) 对 273/280/283/286/287 重算整包 SHA，并索引首个 `TRAILER!!!` 后的 newc 追加记录。每包为 1,223 个不同路径；首段 1,165 个成员之后还有 58 个记录，本轮选取的关键成员没有后续同名覆盖。工具不解包、不执行成员，也不模拟内核硬链接或文件系统展开。

- 五个候选的整包 bytes / SHA 与 loader 路径绑定均匹配。
- 五份 manifest 的 `appfw_future_skip.sha256` 仍为旧修改版 `b1fe2274…`，实际成员是 FX6 原件 `a1c58b69…`。
- `grm_fbinit.member` 是带注释的旧字符串，不能精确绑定成员；其继承 SHA 也不同于实际 shim。287 实际 shim 为 `72,296 B / 46161fe7…`。
- 287 shim 的编译单元名指向 `/tmp/libgrm-fbinit25-287.c`，对应自编源码已保存。缺少完整编译回执，不能声称已证明可重建。

这是元数据陈旧，**不是整包哈希失败或篡改证据**。复跑工具发现这种不一致时返回 1，这是预期的审计结果；它不作运行授权判断。

材料：[287 绑定](candidate287-binding.json)、[四例完整成员核验](representative-member-bindings.json)、[交付文件指纹](DELIVERY-FILES.json)。各组脚本中只搜索首段 archive 的局限已写明，成员覆盖结论以上述完整索引为准。

```sh
python3 -B reports/2026-11-07-fx6-parallel-native-ui/inspect_cpio_binding.py \
  /path/to/cp-helper-agnostic/vm-candidate-gpecap25-287.json
```

## 下一处最小推进点

先保留原厂线程参数和 trampoline，增加观察：匹配 `appFw+0x222dcf4` 的 `osal_create_waitable_thread` 实际 DSO、返回值/handle、调度失败当时的 errno，以及原厂回调、`uxengine_init2`、Arena 注册和数据库加载的进入/返回。负 OSAL 返回、trampoline 前阻塞和 UXEngine 内阻塞应分别判断，避免另起线程掩盖前面的失败。

该链到达后，再观察真实 FX6 presenter 与原生模型，用同一 run 的 guest 帧读回和每步 native key ACK 完成可见、可交互验收。宿主画布、factory scene、整包校验通过和回执回收成功，均不能替代这些证据。

## 验证与官方资料

三个研究任务分别完成实际文件重哈、静态入口/表断言或已结束运行的交叉校验。完整容器工具另通过 7 项合成检查：拼接/覆盖、零填充、可省略 trailer、路径穿越拒绝、截断拒绝、未知尾部拒绝及不支持的 CRC 格式拒绝。未新增 VM、未改运行政策，未做 guest、网页交互或实机验收。

核对官方文档：Linux initramfs 格式允许拼接 archive，且 trailer 可省略；因此不能遇到首个 trailer 就认定整个输入结束。[Linux 内核格式说明](https://www.kernel.org/doc/html/latest/driver-api/early-userspace/buffer-format.html)

QEMU 的 `pmemsave` 可导出 guest 物理内存，GDB 默认使用虚拟地址，物理模式须显式设置；采用何种读回方式仍需绑定实际显示平面和本次 VM 的端点。[QEMU Monitor](https://www.qemu.org/docs/master/system/monitor.html)、[QEMU GDB](https://www.qemu.org/docs/master/system/gdb.html)

这些公共文档只支持格式和工具语义，不证明 Sony 私有 UI 的执行结果。
