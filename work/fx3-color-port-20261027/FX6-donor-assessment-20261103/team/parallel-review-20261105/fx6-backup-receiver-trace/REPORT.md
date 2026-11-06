# FX6 Backup receiver trace: 0x3e014d

- Task：`task_8dd57bb90625`
- Dispatch：`ctx_bb316031f763`
- Status：**receiver 未闭合；不能证明现有 Backup 数据是 appFw 读入来源。**
- 只读；无新 VM/browser/server/QMP/guest/live-process；未改固件/平台/Backup/CPIO/辅助库/运行政策。
- 输入 15 项前后 hash 不变；只写本目录。旧 `fx6-backup-read-contract` 仅读。

## 结论

1. **serial 中 0x3e014d 确实存在，但主要不是 appFw key 请求。** 66ed serial 共 **686** 条 `FX3_UIPC_PASS arg0=0x3e014d`、**12** 条 `FX3_UIPC_SEND_UNIQUE target=0x3e014d`、**39** 个时间窗口。早期 1302/1303/1305/1307 的发送 TID=227，已由 1370 `FX3_UIPC_RECV_BEGIN tid=227 name=bootin.elf` 归属 bootin.elf；不可当 appFw key 请求。
2. **AppFw 的 0x3e014d 发送只有 11783 一条可定位。** `FX3_UIPC_RECV_BEGIN tid=375 name=AppFw`（11659 等）确认 TID 375=AppFw；11783 `SEND_UNIQUE tid=375 target=0x3e014d op=5 tag1=0x20` 位于 3147/3176 两个模型 assert（11686/11736）之后；紧邻窗口**没有**对应 `UIPC_PASS` body、key 或返回。另有 TID=506 的 0x3e014d 发送在 12364/16105，但未定位为 AppFw，不能补成两 key。
3. **无法从 serial 关联两个 key。** 记录中没有 key `0x02cf0214`/`0x02cf0218`；`body_head` 只有 tag/状态低层字节（如 `030000000000000002000000c1ffffff`）。因此不能把早期 bootin 的 0x3e014d 记录、或 11783 单条 AppFw 发送，当作两个 key 的读请求/响应。
4. **用户态最后一个已证边：**
   `libbackup.Backup_nread` VMA `0x24b0`（`0x24e4 bl backup_sync_msg@plt`，w1=`0x3e014d`, w2=`0x1f`, w3=`3`）
   → `libbackup.backup_sync_msg` VMA `0x1a10`（`osal_valloc_msg_wait`/`osal_snd_sync_msg`/`osal_free_msg`）
   → `libosal_uipc.osal_snd_sync_msg` `0x6458` → `__osal_snd_sync_msg` `0x61e8`
   → 目标 bit15=0，走 `0x6390 u_osal_snd_sync_msg` → `0x3a98` 的 `ioctl(fd, 0xffffffff80000005, &req)`。
   serial 的 `FX3_IOCTL_PASS fd=3 request=0xffffffff80000005` 与 `FX3_UIPC_PASS` 与这条边一致；`ioctl-trace.so`（SHA `f2799333…`）preload 定义 `ioctl`，会拦截本次 ioctl，但不提供 Backup_nread。
5. **收端未定位。** 内核 129 个 `.ko` 的地址构造扫描只发现 `0x3e0811`（backup.ko 的 `backup_async_recv`/helper 的 `0x903e0811`），没有 `0x3e014d` 的构造/注册。`backup.ko` 的 `Backup_nread` `.text+0x1eb8`（inner `0x760`）存在，但没有从 0x3e014d UIPC 到它的调用边；`backup.ko.backup_sync_msg` `0x40e8` 是发送方/OSAL 客户端，不是 receiver。`libbkdmn` 的 `BkDmn_Manager` `0x2c30` 收 `0x82cd08e0`，只接 Backup_write/sync，不是 0x3e014d。`fx3-cp-backup-reset-v1.ko` 只处理 `0x903e0811`/op30；`libbackup.Backup_reg_cb` 注册的是 `0x3e414e` async callback，不是 `0x3e014d`。
6. **当前正确表述：** kernel helper 的静态读取契约已核；**appFw → libbackup → osal → ioctl 的发送边已证，ioctl 之后的 0x3e014d 收端/dispatch 未证**。因此 `92fe` Backup 仍是候选输入，**不是已证 appFw 读入来源**；两 key 的数据/返回来源不能确定。

## 精确缺口

- 缺 `osal_reg_msg_queue_cb` / `osal_reg_sync_msg_queue_cb` 对 **0x3e014d** 的注册（回调地址、队列/模块归属）。
- 缺 kernel UIPC 对 0x3e014d 的 dispatch 表项/目标 queue；`osal_uipc` proxy 的接收侧没有闭合。
- 缺带 key `0x02cf0214`/`0x02cf0218` 的请求 body 与配对 response/return；serial 只有 16-byte body_head。
- 缺 AppFw `Backup_nread` 两次调用的 runtime 参数/返回/回调；11783 只有一条 tag1=0x20 的发送，不能替代。
- 缺 `ioctl-trace` 拦截后请求的真实落点（它定义 `ioctl`，但不定义 Backup_nread；是否改变/转发需运行侧证实）。

## 输入/证据

- `receipts/uipc-3e014d-windows.json`：686 pass/12 send/39 windows 的逐条行号、TID、op、tag、body_head、result/errno。
- `receipts/receiver-trace.json`：已知边、被排除的候选、精确 missing_binding。
- `receipts/before-input-seal.json` / `after-input-seal.json` / `input-compare.json`：15 项输入前后一致。
- 关键 SHA：target grmreal46 CPIO `3a08f89d…`；serial `377142e9dcee7f4f7728db6e9fcb822a9f3e501e61da7f719761d4d506f5050e`；libbackup `6a3c5f60…`；libosal_uipc `09ebf598…`；backup.ko `6ae178d5…`；libbkdmn `cc0888d6…`；fx3-cp-backup-reset `7e8d859e…`。
- 未生成 Backup/CPIO、未选数据值、未部署；未新增 patch/veneer/return0/删断言。

## 下一步（若继续）

需要一次受控运行只读观测：在 0x3e014d 的 `osal_reg_*_cb` 注册点/内核 UIPC dispatch 点捕获 callback 地址，并在 AppFw 两次 `Backup_nread` 调用处捕获 key/buffer/返回；或从 `osal_uipc.ko` 的 dispatch table 静态闭合。没有该证据前，不能把 92fe 视为 appFw 来源，也不能据 0x3e014d 日志建立 key 因果。
