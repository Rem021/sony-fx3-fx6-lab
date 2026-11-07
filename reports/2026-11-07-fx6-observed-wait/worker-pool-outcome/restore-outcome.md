# 单变量恢复结果：cold boot 已执行，现卡在 HDMI 格式的 BB 请求回复

**恢复原厂线程池入口后，TID231 `SeqQueueCommon` 已实际执行 `model::sequence_cold_boot::execute`，并进入 `init_hdmi()`。当前等待的是 `adf_set_hdmi_format` 的真实CP回复；它发生在cold-boot promise的fulfill之前。** 因此本轮证明了执行进展，不能只描述为“线程池已创建”，也不能称初始化完成。

本轮候选只移除自有shim在 `appFw+0x12d825c` 的NOP，父链和静态差异见 [恢复候选](../worker-pool-restore-candidate/README.md)。本分析只读已结束运行，未连接VM、未修改冻结输入、未构造消息或回复。

## 运行及来源绑定

- run：`work/fx6-worker-pool-restore-20261107/runs/worker-pool-restore-a3af746e3d`。
- 本次CPIO SHA256：`6c698c7d1d4eac7ff54fc2bd6a54a54c3d4c9156f308aefae96b043ef22c5993`。
- 完整serial SHA256：`2f86db9e4692c333aa17aa8e3e070ffa0705740c8aa8e687dac443b9a6a33b99`。
- receipt：120.209245秒，原因 `wall_timeout`，error=null；QEMU已reap，锁已释放。
- helper枚举129个TID，129次GETREGSET成功、129个不同TID均DETACH rc0，975ms，helper rc0。任务名统计含45个 `SeqQueue*` 及4个 `SeqThreadPool*`；comm只有内核允许的截断长度。

实际CPIO中的appFw SHA仍为 `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`。TID224/227/231的35个PC、LR和记录帧LR全部通过**本次**maps与**本次**CPIO ELF的PT_LOAD唯一解析。例：观察器地址解析为VMA `0x1093c`，文件offset `0x93c`，二者没有混用。RWX运行页允许与原ELF的PF_W不同。

## 真正执行cold boot的硬证据

TID231 `SeqQueueCommon` 的已记录栈，以下为函数内VMA：

```text
libc ioctl +0xc1cbc
  ← libosal_uipc u_osal_rcv_msg_tmo +0x3c9c
  ← libosal_uipc osal_rcv_msg_tmo +0x65a4
  ← observer osal_rcv_msg_tmo +0x1093c (file +0x93c)
  ← appFw +0x20ef7cc        BB send_and_wait_cmp_i
  ← appFw +0x20f160c        adf_set_hdmi_format
  ← appFw +0x20d00e8        BB wrapper
  ← appFw +0x1cd8100        cold_boot::init_hdmi
  ← appFw +0x1cd86a8        cold_boot execute内
  ← appFw +0x1e2528c        原生worker virtual execute之后
```

三个相互独立的身份约束闭合：

1. job constructor的vtable `0x2ec5ee0` RTTI为 `model::sequence_cold_boot`，其execute槽指向 `0x1cd826c`。
2. `0x1e25288` 原生worker读取job vtable+0x10后 `blr x1`；本次栈保存返回地址 `0x1e2528c`，其上层确有cold-boot execute内部返回地址 `0x1cd86a8`。
3. 原厂字符串 `0x25ac4f0` 明确为 `void model::sequence_cold_boot::init_hdmi()`。当前栈中的 `0x1cd80fc → 0x20d00bc` 位于该函数，且 `0x1cd86a4 → 0x1cd80dc` 是execute对init_hdmi的实际调用边。

更关键的是相邻原指令：`0x1cd86a8` 才从job+0x10取promise，`0x1cd86ac → 0x1accea8` 才执行ready+notify。当前线程仍在 `0x1cd86a4` 调用的深层栈中，尚未返回到本次fulfill；这解释了AppFw仍等待同一个future。

## 请求生产者、回复消费者与缺失回复

原厂字符串 `0x2600678` 为 `adf_set_hdmi_format`；`0x2602418` 为 `infra_wrapper_bb::detail::send_and_wait_cmp_i(...)`。静态构造与实际CP日志逐字节一致：

| 项 | 证据 |
|---|---|
| 请求构造 | `0x20f158c`，五个little-endian半字 `{0x200d,0x032d,0x000a,0x8001,0x0000}` |
| 本次原始请求 | `0d202d030a0001800000`，长度10B |
| 目的地 | `0x92840747`，由 `0x20f15f4 / 0x20f1600` 构造 |
| 消息生产 | `0x20ef788..790` 把临时回复队列写成message source；`0x20ef79c → osal_snd_msg` 发向目的地 |
| 回复消费者 | `0x20ef7bc` 取同一回复queue，`0x20ef7c4` timeout=-1，`0x20ef7c8 → osal_rcv_msg_tmo` |
| 本次实际回复queue | CP记录source=`0x81cf610f`，观察器seq9的qid也=`0x81cf610f`，TID231，site=`bb_request_reply` |
| 未回复证据 | CP bridge明确记录该destination `no_reply=1 no_free=1`；观察器seq9只有ENTER，完整serial没有对应EXIT |
| 原件后续消费 | recv返回后按12B复制回复对象，再free原回复；不是回显10B请求即可满足 |

完整serial共9个观察器ENTER、8个EXIT，前8次均rc0并来自libmpr调用点；第9次正是上述BB同步回复等待。不能把前8次真实接收成功延伸成第9次已完成。

当前可以确定**桥接层对这条请求未提供回复**；还未恢复协议正确的12B回复内容、CP处理逻辑或硬件完成条件。不能凭10B请求猜reply、强行让recv返回0或设置ready。model层command type `0x2d` 与这里的CP半字 `0x032d` 属于不同数据域，也不应因低位相似混作同一个ID。

## 另外两个TID如何解释

- **TID224 AppFw**：仍为 pthread_cond_wait → libstdc++ wait → appFw `0x1acd988` → `0x12d9dec` → `0x12da024` → `0xc09de8`。当前不是“pool没创建”的旧状态；其生产者已在TID231执行，但被init_hdmi的reply等待阻住，future尚未fulfill。
- **TID227 SeqThreadPool0**：停在appFw `0x20c455c` 的自身work-available condition，savedLR `0x20c4560`。它是另一条原生pool工作循环；本次cold-boot执行线程是TID231，不能把TID227的空闲等待当成cold boot没运行。

## 结论边界

单变量恢复已把问题从“自身删除原生执行器导致future无生产者”推进到“原厂cold boot实际执行后等待HDMI格式CP回复”。这支持该恢复方向，但当前仍未完成启动或菜单验收；原有其余四处NOP及其它服务缺口依然存在。

没有guest内存 `12d825c` 的指令字节readback；本轮新增的是更强的实际行为反事实：恢复后真实native virtual execute、cold-boot内部帧、HDMI请求和对应无限等待均出现。FP链仅含实际记录的frame，不是完整unwind。

## 重跑及文件

`python3 -B work/fx6-worker-pool-restore-20261107/analyze_restore_outcome.py` 只读取固定run/CPIO并重算证据，不运行VM。

[restore-outcome.json](restore-outcome.json) 保存35个地址的PT_LOAD换算、符号、短指令窗口、精确调用边、packet构造、日志行号、receipt/serial/CPIO指纹；[analyze_restore_outcome.py](analyze_restore_outcome.py) 为独立可重跑脚本。[files.json](files.json) 记录本次正式白名单及来源SHA；未复制CPIO、二进制、原始固件或帧buffer。
