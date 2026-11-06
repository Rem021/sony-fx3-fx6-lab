# FX6 CP helper 单次 VM 测试：CP 绑定成功，AP bootin 已启动

**结论：新 helper 在 FX6 原内核上成功绑定，固定 FX3 CP helper 的 `binding_failure` 已越过；`FX3_AP_NATURAL_BOOTIN_BEGIN` 与 AP launch 已出现。但本次按预设在 AP guard 处停止，未取得 AP 初始化/菜单/完整 FX6 开机证据，目标仍未完成。**

- 唯一 Start：1 次；QEMU exit 0、process reaped、双锁 released。无第二次 Start、无部署、无设备操作。
- 运行目录：本目录（`runs/cp-bind-fc2ad401`）。
- host elapsed：18.257 s；guest 串口时间到 AP guard 约 322 s。

## 关键串口序列

1. `FX3_BACKUP_CP_INSMOD_BEGIN`
2. `[145.134] FX3_SYNC100_API_BIND phase=original result=0 api=ffffff8008322f70 words=b4000b00,a9bb7bfd,910003fd,a90153f3` → 解析到 **FX6** `pcidma_transfer_async` 地址，入口 16B 与 FX3 pin 一致。
3. `FX6_SYNC100_AGNOSTIC_BIND api=0xffffff8008322f70 base=fx6 fallback_zero=0xffffff80083230d0 fallback_nonzero=0xffffff8008322f80 entry16_pinned=1 non_target_dynamic=1`
4. `FX3_SYNC100_API_BIND phase=bound result=0 … words=58000050,d61f0200,004dfd44,ffffff80`
5. `FX3_SYNC100_BACKEND_BOUND exact_op30=1 exact_DMA=1 native_callback_once=1 non_target_original_API=1 synthetic_cp_backup_sync=1 original_CP=0`
6. `FX3_DATE99_WORKER_READY serialized=1`；同一行交织出现 `FX3_BACKUP_CP_INSMOD_RC=0`（严格整行解析因此把它记为 null，但原始字节与 initcall 都明确是 0）。
7. `FX3_BACKUP_CP_PUBLIC_OWNER … result=0`；`initcall init_module+0x0/0x770 [fx6_cp_backup_sync100_agnostic_v1] returned 0 after 22012 usecs`。
8. `FX3_UTIMER_RC=0`、`FX3_BACKUP_ORIGINAL_SEED_BEGIN`、`FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN`。
9. `FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_END`、`FX3_AP_NATURAL_BOOTIN_BEGIN`、`FX3_AP_ARGV_target_qemu_WITH_TRAILING_SPACE_dmode3`、`FX3_AP_BOOTIN_LAUNCH_PID=227`、`FX3_BACKUP_CP_LIVE_OBSERVER_PID=228`。

## 解读边界

- 旧 CP helper 的 `binding_failure` 已不再出现；新 helper 的入口/地址/fallback 绑定有明确日志。
- `FX3_AP_NATURAL_BOOTIN_BEGIN` 只证明 AP 自然启动流程开始，**不证明** AP Init、CAPID、AV/CP 菜单或完整 FX6 开机。
- runner 在 AP guard 处主动停止（`reason=ap_guard_observed_stop`），因此没有 AP 后续串口；这不是 AP 失败，也不是开机成功。
- `run-receipt.json` 中 `cp_helper_rc=null` 是严格整行解析对交织行的漏检；原始串口包含 `FX3_BACKUP_CP_INSMOD_RC=0`，且模块 `initcall ... returned 0`。
- 下一次必须另行授权单次运行，并**不在 AP guard 停止**，等待 AP 初始化/菜单或超时；本轮没有第二次 Start。

## 文件

`command.json`、`serial.log`、`host-stdout.log`、`host-stderr.log`、`run-receipt.json`，哈希见 `RUN-SHA256SUMS`。
