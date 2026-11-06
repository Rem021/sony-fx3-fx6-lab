# AP92：卡检测默认分支与原挂载失败观测

2026-11-02。**已定位本次插入通知来自原检测线程超时后的默认初始化/StartInOut 分支；两次挂载均在原 mcmn_drv_open 失败。未提供无卡模型，画面仍是原厂槽1读卡警告。**

运行 `ap92media-9e1c3a07`，AP90-r2 健康基线，4×A35/MTTCG，300秒窗口，实际301.547秒；不注入按键。两条恢复指令均已处理，没有重复 AP90/AP91。只读原件；无 Git、设备或网络设备操作。

## 运行与回收

- `qemu_exit=0 / process_reaped=true / PID_absent=true / inputs_unchanged=true`；两锁独立重取成功，`missing_markers=[]`（serial 与 printk 两种核对均空）。无提前停止、宿主观察错误、新致命异常或 symbol lookup error。
- 最后完整 `/proc/228/maps` 在 guest uptime297.84s，含原 `/usr/bin/im.elf` 三段映射；299.29s另有未完成的输出段，未把它算作完整存活证据。
- [原回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap92media-9e1c3a07/receipt.json)、[独立复核](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap92media-9e1c3a07-review.json)、[0x11a之后的时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap92media-9e1c3a07-post11a-requests.json)（14048条已保存匹配记录；原上游 trace 有界、serial 可能交错，不声称全系统无损 wire trace）。

## 插入来源：原超时默认路径

以下行号按原 serial 的 LF 分割，未使用会改写行号的通用换行读取。

| 环节 | 实测证据 |
|---|---|
| RM helper | D `f1e4` 两次24B请求头完整；L5805/6684 返回 `0x80000004`。原队列未注册分支在真正发送前返回；`f274` 发送点及回复捕获点均未执行。 |
| 等待超时 | tid337 的原 wait 返回110，L10982 `e9e0` 分支确实执行；随后三次原 `0x80000006` 内部更新（L10987/10999/11010）。 |
| 默认状态 | 原端口 enable 由0变1，三个端口的 hold/port_state/RemoveCnt 保持0；两个媒体记录在 StartInOut 前均 `state=0`、配置 mask=0。不能把这些默认值当作完整原 RM 配置。 |
| 原启动通知 | tid401，media `0x1000` 和 `0x1010` 均实际走 `fa24/status0`，随后 `fa3c/status1`；四条 `d40c` 通知的 hold/RemoveCnt 均0，头24B与payload16B完整保存。 |
| 应用插入 | tid358、source `0x830128`，原 caller `appFw+0x2eacd4c`；L11155/11289 是28B的 `0x10002/0x10003`，完整 raw 已归档。 |

本窗口没有执行 D `e6dc` FRONT 回调，也没有执行 `f380` GetInOutStatus，故没有 FRONT 来源/body 或6B输出可报告。`FRONT_DECODE_AFTER_PORTS` 是观测器给 `10d38` 共用更新点取的标签；本次三条由 `0x80000006` 默认更新到达，**不是收到三条 FRONT 包**。

本次默认分支足以解释应用插入事件；没有证据把它归因为已读到某个插卡 GPIO、真实介质或我们发送了插卡包。设备模型此前缺少原 RM 服务，不能把未知初值解释为诚实无卡。

## 原挂载失败及参数

| media ID /应用槽 | 原公共查询 | 原设备路径 | mcmn_drv_open | Mount最终返回 |
|---|---|---|---|---|
| `0x1000` /槽1 | L18321，wrapper0 / valid1，完整228B | `/nondev/rm3` | L18330，`0x80000004`，handle0 | L18334，`0x7fffffff` |
| `0x1010` /槽2 | L18831，wrapper0 / valid1，完整228B | `/nondev/rm2` | L18840，`0x80000004`，handle0 | L18844，`0x7fffffff` |

这是原设备打开失败，经原转换路径传播；不把返回值再推测成某个未证明的 MMC/文件系统 errno，也不把 `/nondev/rmN` 单独当作完整物理槽配置表。

原 getter 指令在两组基址下用 Unicorn 验证只读地址，另以 setter 原调用/参数ID交叉引用绑定身份；没有调用 getter、GetInstance 或写参数。最后观测值如下（100ms为采样目标，未保证每次瞬态都捕获）：

| 参数ID | current | shadow |
|---|---:|---:|
| 6db / 6dc（挂载状态） | 2 / 2 | 2 / 2 |
| 6e3 / 6e4（媒体错误） | 1 / 1 | 1 / 1 |
| 708 / 709（文件系统挂载状态） | 2 / 2 | 2 / 2 |
| 1203 / 1204（挂载错误） | 0x28 / 0x28 | 0 / 0 |
| 13e / 13f（已收首次通知） | 1 / 1 | 1 / 1 |

L18409 原厂出现 `MOUNT_ERR_EXTMEDIA_SLOT1_FOR_AUTO_TRIGGER`；这些实测值与审计中的警告谓词相符。完整退出条件及 controller 对按键的处理仍未闭合。

## 显示无回归

77条完整 GPE 命令全部 result0：FillRect3、BitBlit73、Flush1；73份144B原参数与AP90逐字节一致。

| op / dst fmt / src fmt | flags | dst在545 / src在545 | 数量 | result |
|---|---:|---|---:|---:|
| FillRect /0/0 | 0xff、0x1ff | 是/否 | 1+2 | 0 |
| BitBlit /0/0 | 0x1000000000001 | 是/否 | 64 | 0 |
| BitBlit /0/2 | 0x10000000e0001 | 是/否 | 9 | 0 |
| Flush /0/0 | 0 | 无像素地址 | 1 | 0 |

QMP物理读回 `0x43feb5100`、614400B、640×480/fmt0、14种像素；SHA256 `fba3e9413bd407b9f113d0792706af6d263319b42286e5ddd1f101239b05b460`，与AP90/91警告图相同，PNG已实际查看。不是菜单/无卡/输入反馈验收。

!['原厂槽1读卡警告，AP92物理读回'](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap92media-9e1c3a07/ap92-QMP-logical-fmt0.png)

## 观测边界与下一步

- 独立 observer v1 的36个D/M点保留原指令、全部GPR/SIMD/NZCV/FPCR/FPSR/SP；guest原ASM自检通过。capid47由v44仅增加弱符号被动调用；去除两处新增文本后协议实现字节一致。宿主ASan/UBSan的长度、地址边界、errno和不改源字节检查通过。
- 新 weak hook 没有输出两条应用插入消息的发送栈，原因未在本轮诊断；不能称发送栈已齐全。原capid的完整28B、tid/source/caller及D原适配器/通知栈已保留。Lead `msg_394ac6fda280` 确认来源证据足够，明确不要求为补栈另跑。
- observer v2及 `ap92-r2-media-native-stack` 候选仅构建，**未启动、未验收**；没有替换本轮当前候选或作为运行成果。
- 最小双空槽输入仍缺：原 `80d9016e` 配置与命令回复封套、配置中media→检测端口的映射、FRONT完整来源/封套与初始化时序。本轮没有编造7B FRONT包、无卡回复、挂载成功或容量信息。等待 Lead 的 `audits/rm-media-service` 与 AP93 合同。

[完整媒体观测/原包/调用栈](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap92media-9e1c3a07-media-observation.json) · [GPE统计](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap92media-9e1c3a07-gpe-statistics.json) · [原指令与参数证据](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap92-passive-original-proof.json) · [静态复跑检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap92-static-replay-check.json) · [宿主检查](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap92-host-check.json)。
