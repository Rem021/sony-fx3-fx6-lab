# 固定 FX3 平台 FX6 双入口零键实验：首次运行失败回执

2026-11-03。**尚无 guest loader、IM 或 IPC 运行证据。** 候选是供体静态审核通过的 `guest-two-entry.cpio` SHA256 `ff2f927de24b801d334ce9111fb486fb2af85d24c509ab20c43eda0a69ffdc40`，只变更 `bootin.elf` 与 `im.elf` 两个等长成员；后者 PT_LOAD 与 FX3 逐字相同。实验保持固定 FX3 内核、完整 DTB、QEMU、CPU×4、5120MiB、GICv2、环境和 Backup，原命令只允许 serial 与 CPIO 路径变化。原 `cpio_audit.audit()` 实际返回 1140 成员、20 个原 ELF、两个精确身份差异、父目录顺序错误为 0、`safe_to_unpack=false`；隔离放行必须同时匹配独立 donor `review.py` 的两个 SHA/字节数，不放松其余拒绝条件。

首次宿主预检产生 `runs/fx6entry-e5cd066a/preflight-failure.json`：误将允许变化的 CPIO 文件名也与冻结命令比较，故在 QEMU 创建前拒绝。修正为只比较 loader 地址与 `force-raw` 尾项后，独立离线测试确认实际变更索引仅 `[20,31]`，完整 DTB/内核未变。该预检不算 guest 轮。

唯一实际 QEMU 轮 `runs/fx6entry-b3256731/receipt.json`：PID 30381，5.554 秒，`-S` 停在初始暂停态，宿主 `QMP` 用过长绝对 AF_UNIX 路径导致 `OSError('AF_UNIX path too long')`，在 `cont` 前终止。serial 文件 0 字节 SHA256 `e3b0c442…`，三个 loader RC、自然 bootin、IM maps 和首个 IPC 全部 **unknown/未观察**；零键、零合成事件。QEMU exit 0、reaped、PID absent，输入 SHA 未变，两把原锁 free；本轮未能经 QMP 核验 API16，`API16_restored=false`，不能称生命周期通过。旧 runner 源在该 run 的 `observer-source.py`，原始错误保留。

新 runner 已离线修复为与原 runner 同样先临时切到 run cwd、以短名 `q` 连接、再恢复 cwd；本地 mock AF_UNIX 服务器验证握手、`qmp_capabilities`/`cont` 两条 QMP 响应以及 cwd 还原通过，修正后 runner SHA256 `3bdc9121ac331a947fc157fc5aa1455a531140a0d2700dd1fed77f9db1f37a5e`。**未据此再启动 QEMU**。若需真正回答 loader/IM/IPC，需协调者另授权一次顺序有界运行；本轮失败不可算作入口通过。
