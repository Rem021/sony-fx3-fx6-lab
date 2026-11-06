# FX6 内核 + FX6 appFw + 新 CP helper：已执行到 assert1075

**结论：FX6 原 appFw 已在新 CP helper 与 FX6 内核上实际装载并执行，越过 CP helper；但仍在已知的 `infra_wrapper_bb_procam_chaplin_base.cpp:1075` 发送/等待断言停住。没有 FX6 菜单或完整开机证据，目标未完成。**

- 唯一 Start；QEMU exit 0、process reaped、双锁 released；host 180.16 s，serial 4,006,697 B。
- CP helper：`FX6_SYNC100_AGNOSTIC_BIND api=0xffffff8008322f70`，`FX3_SYNC100_BACKEND_BOUND`，`FX3_BACKUP_CP_INSMOD_RC=0`。
- FX6 appFw：`/usr/lib/appFw.so` 已映射；出现 `FX3_PROFILE_FRAME ... module=/usr/lib/appFw.so`、`FX3_PROVIDER_CALLER`、`appFw.so` 调用栈。
- 停点：`send_and_wait_cmp_i(OSAL_ID, const void*, int32_t, void*, int32_t)`；请求 destination `0x92840747`、source `0x81cf6196`、10B raw `0d202d030a0001800000`；`dispatch_pending=1` 后 `assert at ...:1075`，发送返回非零，未进入 `osal_rcv_msg_tmo`。
- 之后没有 `FX3_AP89_SCREEN_CREATE`/`FX3_MEDIA_START_BRANCH`/菜单，AP 仍在轮询但未完成初始化。
- 这与历史 FX6 AP 首断言相同；新 CP helper 解决的是更早的 CP `binding_failure`，不是这个 CAPID 发送断言。

**下一步**：先做只读分支/字段观测（CAPID `osal_snd_msg` 返回、`audio_dispatch` 的 `model+0x18`/owner、AP `0x20ef7a0` 的 w0），再决定 FX6 上层的字段级初始化/回复适配；不得手填 `initialized=1` 或伪造 `0x132d` 而不验证。
