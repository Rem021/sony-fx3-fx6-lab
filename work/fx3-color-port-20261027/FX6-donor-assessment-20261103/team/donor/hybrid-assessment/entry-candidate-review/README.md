# FX6 两入口候选独立审核（静态）

2026-11-03。运行 `python3 -B review.py` 得到 [receipt.json](receipt.json)：`PASS_STATIC_TWO_ENTRY_ALLOWLIST_ONLY`。这是独立解析两个 newc CPIO、逐成员与逐字节比较、核对 FX6 原件和固定平台哈希的结果；未启动 QEMU，未验证动态装载、进程、IPC 或画面。[handoff.json](handoff.json) 是给唯一 runtime 负责人的待执行计划，不是运行回执。

## 候选的实际差分

源 `guest.cpio` SHA256 `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d`；候选 `guest-two-entry.cpio` SHA256 `ff2f927de24b801d334ce9111fb486fb2af85d24c509ab20c43eda0a69ffdc40`。两者均为 453,184,500 字节、1,140 成员；成员顺序、头、符号链接、padding、trailer 和以下两段 payload 以外的所有字节相同。

| 唯一变化成员 | CPIO payload 半开区间 | 字节数 | FX3 SHA256 | FX6 原件 SHA256 | 实际不同字节 |
| --- | ---: | ---: | --- | --- | ---: |
| `usr/bin/bootin.elf` | `[16071088,16095048)` | 23,960 | `dab3ce4b6c28a6c9ffd9f0b893dce1d08f3ee7302a09df87e518409e728be2f2` | `72480247f8d2a1eeaab076b880c35279c6c94284649e267066f5ea10de6622a6` | 977／74 连续段 |
| `usr/bin/im.elf` | `[17220920,17261840)` | 40,920 | `5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91` | `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec` | 6／2 连续段 |

**关键修正：FX6 `im.elf` 的两个 ELF `PT_LOAD` 文件段与 FX3 逐字相同。** 六处差异均在不装载的 `.comment`（ELF 文件偏移 38745–38749 和 38771），是编译器标记变化。`bootin.elf` 则有装载的 `.text`、`.rodata` 和 `.data` 差异。因此候选虽有两个 FX6 文件 SHA，新增的可执行入口行为实际只可能来自 `bootin.elf`；不能据此声称已换入 FX6 IM 逻辑。两者均是 AArch64 ELF，解释器 `/lib/ld-linux-aarch64.so.1` 与各自 FX3 对应文件的 `DT_NEEDED` 名称相同；这只是静态装载前提，不证明符号版本、预载钩子或运行 ABI 成功。

## 固定部分及第一道门

固定 baseline JSON SHA256 `854e58f0485537e4644f81daa51d532eea5fa1f5e30887c684e9356e542b9669`；审计时 QEMU `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d`、FX3 kernel `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c`、完整 DTB `b6f9f4c04d0da101565d67244629a0ad7a3954c8af004f353c16ae0c8b499de7`、Backup `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f` 均与 baseline 相符。候选保留原 `/init` SHA `8ad0be3aec240977060e25ba1193ad80f6ef596ffe47392e3d5b5b79c0ee4a05`、FX3 `appFw.so` SHA `545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f`、`libObj.so` SHA `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae`、FX3 Backup/模块和 `/init` 中 17 个预载文件。未携 FX6 AP、AV、CP；即使看到菜单也是 FX3 AP。等长替换使 initrd 总长不变，未产生修改 DTB `initrd-end` 的理由。

原 FX3 ELF 身份基线 CPIO SHA256 `7d151d8f1e363c66a947724fd65c5b818e8037347c886d8b0f133c970ad1f862` 含 20 个 ELF；旧 `cpio_audit.py` 对新候选会准确报 `bootin.elf`、`im.elf` 两项改变，`safe_to_unpack=false`，父目录顺序错误为零。运行方必须保留旧审计中全部其他失败条件，另用 [review.py](review.py) 的精确两项旧/新 SHA 与长度允许清单作为隔离放行条件；不得全局关掉 ELF 身份门或忽略其他错误。主控 `build.py` SHA256 `8a54dc4b67c5f9f9584f5b5f2ddbbf8d64bcd7d676393b0baf7eaa53eae4f6b4`、manifest SHA256 `de1b7cacc595903e01c8db3e927893bc37232949846ae4005818e7ccd513e5d2` 已只读核对；本脚本没有调用其验证器或修改候选。

## 唯一 runtime 负责人的最小交接

待 FX3 MSS 补测结束、双锁可用，由原 runtime 负责人按 [handoff.json](handoff.json) 执行一次无方向键、无人工事件的 host-only 观察。冻结命令只替换 argv[31] 的 CPIO 文件路径（维持 `addr=0x440000000,force-raw=on`）和 argv[20] 的全新 serial 路径；QEMU、FX3 kernel、完整 DTB、机型参数、环境、原 `/init`、17 预载、Backup 与其余 argv 保持原值，QMP/GDB 相对套接字落在新运行目录。先记录 `/init` 的 loader `--verify`、`--list`、BusyBox `true` 三个 RC；若任一非零即按原拒绝门停。若过门，只观察自然 `bootin` 入口、`im.elf` 进程/maps 和首个可见真实 IPC（如自然出现的 `FX3_BOOT_QUEUE_SEND`），不制造事件；该标记覆盖的只是特定发送边，缺席不代表无 IPC。首个真实故障或首个有界入口证据即停，host 上限 180 秒；按既有 API16 恢复并回收自身 PID，确认双锁释放，命令、哈希、serial、RC、API16/锁回执只存新目录，不覆盖旧 serial。

旧构建器生成候选属于**静态文件证据**；本回执独立确认字节边界与固定平台。下一步真正需要的是 runtime owner 的 loader RC 与首个自然入口/IPC 证据；未得到之前，兼容性与 FX6 系统启动均为未知。
