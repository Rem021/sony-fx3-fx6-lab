# FX6 运行证据与原生显示链复核（2026-11-07）

结论：273、280、283、286 四个已结束实验均未证明原厂 FX6 菜单可见或可用。现有网页三屏来自宿主 Python/Pillow 绘制。前端显示参数变化不能证明原生相机模型发生变化。

本次只读分析，没有启动、停止、暂停虚拟机，没有接入 GDB/QMP/HTTP，也没有修改 donor、前端或共享库。未审计正在运行的实验。写入前确认外盘 UUID 为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。

## 可复核交付

- `summarize_evidence.py`：只读 newc 成员指纹、完成回执、串口与前端 AST 摘要器。
- `summary.json`：四例输入指纹、明确日志行号、帧统计、源码函数位置和调用关系。
- 仅保存自建脚本、指纹与少量诊断日志摘要；没有提取固件文件到交付目录。

复跑（在仓库根）：

```sh
python3 -B work/parallel-research-20261107/runtime-evidence/summarize_evidence.py \
  --root /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic \
  --frontend outputs/fx3-vm-trial/run_fx6_menu_trial.py
```

只把 `process_reaped=true AND locks_released=true` 的回执当成已结束实验。对每例重算 manifest、CPIO、serial 的 SHA-256，并检查实际命令的 loader 路径。四例全部匹配；被读取的输入在读取前后大小和 mtime 均未变化。这确认了当前磁盘材料的一致性，不能独立证明历史 loader 当时验证了所有输入字节。

**成员扫描范围只到第一个 newc `TRAILER!!!`**，不解析其后追加的 archive/member。整包 SHA 覆盖全部字节，但这里的成员指纹不能独立证明 guest 最终覆盖后的有效文件。协调者的 `inspect_cpio_binding.py` 负责完整容器/追加区核验；本脚本不替代它。

四份 CPIO 的第一个 newc archive 中 `usr/lib/appFw.so` 完全相同：50,520,424 B，SHA-256 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`。

## 四个代表运行

| Candidate / run | 已观察到的直接证据 | 解释边界 |
| --- | --- | --- |
| 273 / `cp-bind-a11cd595` | serial:877 `FX6_APPFW_LAUNCH_DONE`；1599 `SEGV (PC=...)`；gpe0 全零 | 通用异常前 current task 是 busybox，不能据此认定 appFw 崩溃；launch done 也不证明 UI 初始化完成 |
| 280 / `cp-bind-44c98718` | serial:1480 `FX6_APP_CONFIG_ENTRY arg=AppConfig.so`；1481 `FX6_OSAL_THREAD_DIRECT ... entry=0x7f79b80bbe`；1482 `APPFW_SEGV sig=7`，PC 同 entry | 这是可直接归属 appFw 的异常；记录的 appFw 基址为 `0x7f77287000`，相对 PC `+0x28f9bbe`，末位未按 AArch64 指令 4 字节对齐。ABI/结构体字段误读是待验证假说 |
| 283 / `cp-bind-bc7bc525` | 多次 `FX6_BMP_STUB30_LOADED`；1725 busybox SEGV；gpe0 全零 | 不能只凭重复 preload 行断定重启根因；没有绑定到原厂 screen 的成功绘制证据 |
| 286 / `cp-bind-1beab982` | serial:845 `FX6_APPFW_DEFERRED_UNTIL_MODULES`；1213 `appfw-launch: stub dlsym failed: /usr/lib/libgrm-fbinit9.so: undefined symbol: Application_System_Init`；1634 busybox SEGV；gpe0 全零 | dlsym 失败是直接的入口调用阻塞；后面的 busybox 异常应另列，不能合并成 appFw 断言 |

四例都因观察墙钟预算结束（150s / 150s / 150s / 120s）；QEMU 的结束与回收不表示 guest 应用正常退出。每例 `gpe0.bin` 为 2,211,840 B，非零字节数为 0。该采样区域全零只能说明该区域在采样时没有可见像素，不能证明不存在其他显示平面。

两个独立的记录缺陷：

1. 四例 `receipt.serial_observation.fault_markers=[]`，串口却都有 `SEGV (PC=...)`。自动摘要漏报；不得再以该空列表证明无故障。必须同时保留异常归属（busybox / appFw / kernel），避免把所有 SEGV 都归为 appFw。
2. 四份 manifest 的 `grm_fbinit.sha256` 都是继承值 `ca4d57...`（标注 content=fbinit8），与第一个 archive 的 shim member 不符。该 member 为 273 `f6ff5159...`、280 `d5cc798b...`、283/286 `b0c9187f...`。CPIO 整包 SHA 校验全部匹配，因此这是成员元数据陈旧的证据，不能表述为整包被篡改或运行输入不匹配；仍需全容器扫描排除追加成员覆盖。

## 当前网页的真实数据流

审计源码 SHA-256：`7f6536615bbaa179037f931f992d3513e1f695a122183367d49efdfc9b9311ef`（68,669 B）。行号只对应此版本。

- `/frame.png`（1483）调用 `session.get_png()`（852），直接返回 `_current_png`。四处 `_current_png` 赋值（696、718、805、840）均为 `render_current_screen_png(self.state)`。该函数路由到三个 Pillow 绘图函数；没有 VM framebuffer 读回。
- `set_page`（710）和 `select_box_or_param`（818）修改宿主 state 并重绘，不向 guest 发操作。页面/热区切换成功仅证明宿主逻辑工作。
- `apply_key`（730）首先修改宿主 state；只有在 `vm_running AND vm_ready` 时尝试写入 guest 自建 mailbox `0x41e000f00` 与 key payload `0x41df00008`，随后仍调用同一宿主绘图函数。没有读取原生模型状态或确认屏幕转换。
- `write_mailbox_and_key`（635）只提交 GDB `M` 包，返回传输层响应；没有读取 step ACK 或确认 key 被原厂 receiver 消费。`_update_frame_label` 只检查字典无 `error`，即使 `M` 返回 `E..` 也可能显示已同步。
- `vm_ready`（`_vm_worker`，922）由串口出现 `FX6_OSD_FLUSH` 或 `FX6_GPE_FILLRECT` 设置；没有校验原生 screen、frame 或模型。factory scene 原语也可能满足该条件。
- 另有端点不一致：`apply_key`（794）固定连接 `tcp:127.0.0.1:1234`；`start_live_vm`（886）优先选择 277 清单，而其 QEMU 参数为 `-chardev socket,path=g,... -gdb chardev:keygate93`。worker 未重写 GDB 参数。Unix socket 与固定 TCP 不是同一端点；当前源码不支持把写入成功视为已连接本次 VM 的证明。

因此界面标注中的原厂布局、字体或控件命名不能作为原厂代码执行证据，当前三屏 PNG 的 SHA 也只绑定宿主生成图片。

## 下一次真实菜单验收所需的最少证据

1. **运行绑定**：run id、候选清单 SHA、实际 CPIO SHA、CPIO 内 appFw/shim/resource 指纹，以及本次 QEMU socket 的精确路径。
2. **原厂入口**：证明加载 `AppConfig.so` 相机 UI（而非 AdjChkConfig 工厂 scene），原厂 UI worker、screen/controller/presenter 的可定位观察；区分 native code 与 shim 生成的日志。
3. **原厂状态**：记录目标 screen 或 view id 与至少一项原生模型值。单凭自建 mailbox 内容不够。
4. **帧来源**：run-bound guest 显示缓冲地址、pitch、像素格式、宽高、采样序号/时间、完整 bytes SHA 与导出图；前端应仅显示该读回帧，PNG 能回溯至同一原始帧。
5. **交互闭环**：每步 key 的 attempt/step、传输响应、native receiver ACK、原生 screen/model 的变化、后续帧变化。宿主 state 不能作为 guest 变化的替代证据。
6. **故障与结束**：保留 raw serial 和所有 assert/SEGV/Oops 的归属，记录观察预算、guest 与 QEMU 各自的结束状态及回收结果。初始化/可见/可交互应分别判定。

建议现阶段优先修正入口符号与 OSAL 线程 ABI，并离线更新候选成员指纹与串口故障归属；在下一次真实运行前准备 guest frame 读回和 step ACK 记录。此复核没有提出或执行相机刷写。
