# FX6 CP helper 地址无关候选：CP 绑定成功，FX6 appFw 已执行到 CAPID assert1075

**结论：新 helper 在 FX6 原内核上成功绑定，固定 FX3 CP helper 的 `binding_failure` 已越过；第一次运行到达 AP natural bootin，第三次运行（FX6 内核 + FX6 appFw + 新 helper）已实际执行 `/usr/lib/appFw.so`，但停在已知的 `infra_wrapper_bb_procam_chaplin_base.cpp:1075` CAPID 发送断言。未取得 AP 初始化成功、菜单或完整 FX6 开机证据；目标仍未完成。**

候选目录：
`work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fx6-boot-readiness/early-kernel/cp-helper-agnostic/`

## 候选与离线验证

| 项目 | 值 |
|---|---|
| 旧 helper | `f4d7a1fa048d3548840fb2b9dd91e9538b19a34e48089a01ee466c02d3c277ca`，190,648 B |
| 新 helper | `7e8d859ecb0fc66c5e05909ae5688b966838a6aa7bb0a478b6b4139177004aaa`，66,552 B |
| 新 CPIO | `11adfbcec5fc1a73e60c96ed7cebb361ce53498d0b110793bf665da1b69756c0`，453,184,500 B |
| 输入 CPIO | `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d`，453,184,500 B |
| 模块 ABI | `ELF64 AArch64 relocatable`；`vermagic=4.9.337-scel+ SMP preempt mod_unload aarch64`；`depends=osal_uipc`；内部名 `fx6_cp_backup_sync100_agnostic_v1` |

- 入口接受 FX3 `0xffffff80083220c8` 或 FX6 `0xffffff8008322f70`，仍 pin 16 字节入口；两版前 0x200 字节逐字节相同。
- fallback 改为运行时 `api+0x160` / `api+0x10`，不再硬编码 FX3 绝对地址。
- CPIO 只替换目标成员；其他 1140 个成员逐字节一致，`TRAILER!!!` 保留，尾部 124,096 B 零填充，总长精确 453,184,500。
- 宿主测试以 FX3/FX6 地址分别编译运行，均 exit 0；覆盖 40B schema、DMA copy、锁/回滚、错误路径、非目标 fallback、cleanup restore，并断言 fallback 全局值。

## 唯一一次真实 VM 运行

运行：`.../cp-helper-agnostic/runs/cp-bind-fc2ad401/`；QEMU exit 0、process reaped、双锁 released；host 18.257 s。

关键串口：

1. `FX3_SYNC100_API_BIND phase=original result=0 api=ffffff8008322f70 words=b4000b00,a9bb7bfd,910003fd,a90153f3`
2. `FX6_SYNC100_AGNOSTIC_BIND api=0xffffff8008322f70 base=fx6 fallback_zero=0xffffff80083230d0 fallback_nonzero=0xffffff8008322f80 entry16_pinned=1 non_target_dynamic=1`
3. `FX3_SYNC100_API_BIND phase=bound result=0 … words=58000050,d61f0200,004dfd44,ffffff80`
4. `FX3_SYNC100_BACKEND_BOUND exact_op30=1 exact_DMA=1 native_callback_once=1 non_target_original_API=1 synthetic_cp_backup_sync=1 original_CP=0`
5. `FX3_BACKUP_CP_INSMOD_RC=0`（原始串口；严格整行解析因交织漏记）、`FX3_BACKUP_CP_PUBLIC_OWNER result=0`、`initcall … [fx6_cp_backup_sync100_agnostic_v1] returned 0`。
6. `FX3_UTIMER_RC=0`、`FX3_BACKUP_ORIGINAL_SEED_BEGIN`、`FX3_AP101_NATIVE_LOAD_READBACK_WINDOW_BEGIN/END`、`FX3_AP_NATURAL_BOOTIN_BEGIN`、`FX3_AP_BOOTIN_LAUNCH_PID=227`、`FX3_BACKUP_CP_LIVE_OBSERVER_PID=228`。

运行回执/串口哈希：
- `serial.log` `cd7f42b0f1e15670b0e4b47bf8276477c5c1fd520b933dd457087725e4dce800`，97,889 B。
- `run-receipt.json` `0612635e002a5aa1fbb39c1d40eda90fdb2550d2835c1aa202d7225e25a165a8`。
- `RESULT.json` 在运行目录；`RUN-SHA256SUMS` 7 项校验通过。


## 第三次运行：FX6 appFw 实际执行，停在 assert1075

- 新 CPIO `guest-hybrid-fx6kernel.cpio`：源 `hybrid-ap-candidate/guest-three-entry.cpio`（`bb618bd2…3fff02`，含 FX6 `bootin/im/appFw`），仅替换 CP helper；总长 453,184,500 B，其他 1139 个成员逐字节一致。
- 运行 `runs/cp-bind-6e83a14a`：QEMU exit 0、reaped、双锁 released；host 180.16 s；serial 4,006,697 B，SHA `961baa1b05446f8af09413f4cee141a6b069b3afd4dc244a2c7d2258996ba17c`。
- CP helper 绑定成功；`/usr/lib/appFw.so` 已映射，串口出现 `FX3_PROFILE_FRAME … module=/usr/lib/appFw.so` 与 `FX3_PROVIDER_CALLER`。
- 停点：`assert at infra_wrapper_bb_procam_chaplin_base.cpp:1075`，函数 `send_and_wait_cmp_i`；向 `0x92840747` 发送 10B `0d202d030a0001800000`（source `0x81cf6196`）后发送返回非零，未进入 `osal_rcv_msg_tmo`。
- 没有 `FX3_AP89_SCREEN_CREATE`、`FX3_MEDIA_START_BRANCH` 或菜单。CAPID helper 的 `FX3_CAPID_BIND` 在本轮前期未出现；断言发生在 CAPID 音频初始化/回复之前。
- 这不是 CP 失败，而是既有的 FX6 AP CAPID 发送/初始化边界。下一步必须先做只读分支/字段观测（`osal_snd_msg` 返回、`audio_dispatch` 的 `model+0x18`/owner、AP `0x20ef7a0` 的 w0），再做字段级适配；不得手填 `initialized=1` 或伪造 `0x132d`。

## 边界

- `FX3_AP_NATURAL_BOOTIN_BEGIN` 只证明 AP 自然启动流程开始；**不证明** AP Init、CAPID、AV/CP 菜单或完整 FX6 开机。
- runner 在 AP guard 处主动停止；没有 AP 后续串口，这不是 AP 失败，也不是开机成功。
- 本轮只授权/执行一次 VM；没有第二次 Start、没有部署、没有设备操作。

## 下一步

第三关是 CAPID：在 FX6 appFw 的 `send_and_wait_cmp_i` 10B 请求前完成正确初始化/回复，或做字段级转换；先观测实际返回/字段，不手填成功。只有 CAPID 通过并出现 FX6 菜单/初始化证据，才可继续谈完整开机。

`SHA256SUMS` 封存本报告；候选目录的 49 项 `SHA256SUMS` 已包含本次运行证据。
