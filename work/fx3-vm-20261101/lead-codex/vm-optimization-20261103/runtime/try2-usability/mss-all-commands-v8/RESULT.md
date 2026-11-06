# FX3 MSS 同队列全命令被动观测（2026-11-03）

**结果：两个有界诊断轮都干净退出，但都未发送实际按键，MENU／LEFT／DOWN 对计时的运行对照仍未完成。** v8 被动探针真实装入原 FX3 guest 后，在启动期捕获到 `0x80924220` 的 20 组入口／返回，分别是 `0x00920118` 7 组、`0x00920119` 5 组、`0x00920202` 6 组、`0x00920204` 2 组；两轮相同。这证明 v7 的单命令过滤确实漏掉了同一原 app 构造器的其他发送调用，**不证明 UPM 已消费或计时器已更新**。20 组 `return x0=0`，但 `raw_ok=0` 全部成立，线上 16B 原包与内核处理仍为 unknown。未注入任何 MSS 请求、keepalive 或键。

## 原字与候选差分

- 原 `appFw.so` SHA256 `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`；普通指令挂点 `0x2d35168=a9bc7bfd`、`0x2eb4f58=72b01240`、`0x2eaf294=a9ba7bfd`、`0x2eaf308=7100001f` 已逐字独立核对。原 `0x2eaf2fc/300` 写 16B，`304` 调用 `osal_snd_sync_msg`，`308` 在调用返回后比较，`334..33c` 才是本函数释放；故 v8 沿用这四个普通指令点，未增 BL 探针，也未把不可读解释成已释放。
- 原 `upm.ko` SHA256 `ba0cca76ec8e19836697d69d0851c5a0bd2c2eea98ee2aa54d1eff3408f1ec8e`。本轮独立定向反汇编 `.text+0x2180..0x26e8` 见 `original-upm-dispatch.txt`：`0x21f0/0x2204` 比对 `0x00920118/119`，`0x2214/0x2224` 分派 `0x00920202/203`，`0x23ac` 比对 `0x00920204` 并分支 `0x24d0`；`0x24e8` 调用 `k_mss_reload_timer_nr`。这是原静态分派，当前探针只在 app 发送端，不含内核接收观察。
- v7 源 SHA256 `c5de178004eac532832e0f166eecee8ebf250becae1c8099f849b5047d26e653`，v8 源 SHA256 `cf2987d87a4e1ac8993e998f71a53504a91dba8d1249886c564bbed9375b4e6a`、so SHA256 `c6ffd64d50292f429e2a75939c13a6490599b5462bf88ca5ba7b4f2a1105b652`。`source.diff` 仅扩大过滤为 `qid==0x80924220`，加同线程 `call_id/qid/cmd/source` 入口返回关联；256 项有限 ring、异步打印和 overflow 标记保留，原返回值不改。两轮 `overflow=0`，`raw_ok=0` 绝不称真实包。
- 新候选 `vmopt-20261103-try2-mss-all-v3/candidate.json` SHA256 `2382063eacb5f185e8553c2596be2c644654efe7234adc1e4578f7464ab99a05`；`preflight.json`、`build-receipt.json` 和 CPIO audit 验证相对 v7 仅一个观察 so 成员变化、DTB 仅 initrd-end 变化。QEMU、原内核、FX3 cortex-a35×4、5120MiB、virt/GICv2、MTTCG 无 icount、固定 English generation4 Backup SHA `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f` 与 v7 一致。未动原固件、原种子、旧候选、FX6 平台或用户 TRY2 入口。

## 两轮实际资源与首故障

| 轮次 | guest／画面证据 | 首故障与实际按键 | 退出回执 |
|---|---|---|---|
| `try2mssallinternal-48a838e5` | serial SHA256 `4452b928c28f9c6cfbdad5380678cbb84219722e1efbc783a161e8f84bd331e0`；MSS 20 对，guest `29.428843..36.127939s`；最初待机 PNG seq5 SHA `2914275c`，请求快照 seq548 SHA `e0140ea1` 是仅剩右下图标的近黑图，seq551 在 0.413s 后恢复同一完整待机像素。无原生 `MODEL_POWER_OFF`／shutdown。 | 新 runner 错把**本轮 12 键人工预算**当作底层 `InputGate.max_steps=12`；原 `valid_command` 合法容量是 32..4096，故首请求写 guest 前报 `白名单、步数或按键持续时间校验失败`。首请求的近黑图此前未实际审阅；**key_steps=0**。 | host 109.328s＜900s，PID14920 exit0/reaped/absent，20s guest ack/API16 恢复、输入 hash 未变、双锁 free；receipt 的 `host_error` 与 `health_pass=false` 不能当 guest 故障。 |
| `try2mssallinternal-c017e6ed` | serial SHA256 `4f7d1745806314521f43257eec20ac69581119181057ad1d191549afab3ceac0`；MSS 同样 20 对，guest `29.823945..36.181253s`。冻结待机 PNG seq240 SHA `2914275c` 已用图像工具查看；提交时 seq655 仍是该像素，runner 检查时 seq663 已是近黑 SHA `e0140ea1`、间隔 0.519s，故原门正确拒绝。无原生电源关机。 | 离线修正后底层容量保留32，独立 host 实际键预算12；`internal-stale-01-*` 明记 `current_committed_frame_changed/stale_no_guest_write`。按首错停止，**key_steps=0**。STOP_FOR_REVIEW 原文字把它写成仅序号前进，准确原因是 runner 检查时像素也已变化，以该 stale JSON 和本报告为准。 | host 148.097s＜900s，PID19059 exit0/reaped/absent，20s guest ack/API16 恢复、输入 hash 未变、双锁 free；`health_failure` 来自主动 STOP_FOR_REVIEW，不是 APO 或工具超时。 |

两轮 original PNG 均已用图像工具查看；近黑帧由 guest 原生 OSD ring 的 `0x1005` 提交产生，`all_zero_pixels=false` 且右下图标仍在，不能称浏览器加载、关机或已证渲染故障。它与完整待机帧短时交替，在请求与 runner 复核之间造成真实像素身份变化。当前不降低像素门，也不根据旧截图继续按键。

## 离线修正与剩余门

- `run_trial_v14_mss_all.py` 的错误 runner 快照已保留在第一轮 `observer-source/`；独立 `run_trial_v15_mss_all.py` 在启动前核对底层容量32及第1/12键合同，另在 host 循环限制最多12次实际请求。`--max-steps 12` 的非法参数已离线复现并在 QEMU 启动前拒绝；`offline-host-gates.json` 验证底层32可接受第1/12步。此 v15 版本确在补测轮运行且收尾通过，但没有成功送键。
- `freeze_view_v15_mss_all.py` 生成不可变逐键 PNG；提交辅助 `submit_after_view_v16_mss_all.py` 对已看 PNG 与当前像素 SHA 作等值检查，可容忍**像素完全相同**时序号前进，像素不同则不发请求。离线 fixture 通过“同像素新序号接受／异像素拒绝”，真实补测也证明 runner 最终像素门仍有效。`runner-capacity.diff`、`submit-freeze.diff` 与 `offline-host-gates.json` 留证。
- **仍未通过**：MENU、LEFT、DOWN 各键后的 MSS 同队列命令对照，UPM consume／timer start 与实际 5 Min 重置，任何长期可用性或网页联动验收。两轮启动期 `0x00920204` 的存在不代表菜单操作触发该命令。若以后再测，须先处理原 OSD 近黑短帧与人工审阅时点的竞态，保持当前像素身份门和单键决策；本任务不再启动第三轮。
