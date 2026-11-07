# 仅恢复原厂 cold-boot 执行器的候选

本候选从已运行并封存的 wait-snapshot295 克隆，**只将自有 shim 对 `appFw+0x12d825c` 的 NOP 删除**。该处原厂 `BL 0x1d96370` 将重新获得执行机会，创建原生45线程池；本构建子任务未启动或接入VM，不能声称线程已经创建、future已经完成或UI已恢复。

- manifest：[candidate-manifest.json](candidate-manifest.json)，schema `fx6-worker-pool-restore-candidate-v1`，状态 `PREPARED_WORKER_POOL_RESTORE`，模式 `worker-pool-restore`。
- manifest SHA256：`8f3dc13a934a5d35110b7527bbae9a913c1ffdbb462a3646d4066949b462dcc1`。
- derived CPIO SHA256：`6c698c7d1d4eac7ff54fc2bd6a54a54c3d4c9156f308aefae96b043ef22c5993`。
- 新 shim 79704B SHA256：`0f2d372411e09a1aeb387a38ba7c48a3f943e5b0c2612548d965f8aa98927c9d`。

## 为什么恢复这一处

实际TID224栈绑定 `model::model_future::wait()`，本次future的生产者是原厂 `model::sequence_cold_boot`。type0x2d经过原生dispatcher，入pool index0；完成路径会对同一promise写ready并notify。295恰好NOP了创建整个pool的调用，当前快照只有4个TID，缺少其45个worker。完整证据见 [wait-chain](../analysis/wait-chain/wait-chain.md)。这支持优先恢复自身删除的执行器，不把MWF/外部服务缺口自动认作当前等待的直接根因。

恢复pool之后，cold boot仍可能在剩余infrastructure缺口阻塞。下一轮应观察真实新增线程/worker entry及future进展；少一条NOP日志本身不能证明原厂调用已执行。

## 唯一源码变化

[源码差异](source-change.diff) 严格只有两行：`offs[5]` 改为 `[4]` 并删除 `0x12d825c`，该patcher的 `i<5` 改为 `i<4`。由于原数组长度与循环上限都写死为5，必须同步改这两行，避免隐式0元素或越界；没有使用重复NOP地址替代。

剩余四点为 `0x12d824c / 0x12d8250 / 0x12d8254 / 0xc09e50`。所有其它shim源码，包括Backup、MWF guard及其它替代行为原样保持；原appFw payload、观察器、GOT诊断launcher、init和一次性快照helper均逐字节保留。没有改ready、notify、消息、返回值，也没有直接改写真实Sony ELF中的任意分支。

## 来源与冷核验

- [baseline-reproduction.json](baseline-reproduction.json)：冻结的295源码重编后，实际snapshot shim的全部 **17个SHF_ALLOC节** 在类型、flags、VMA、大小和有文件内容时的字节上全部一致；包括`.text/.rodata/.got.plt/dynsym/hash/relocations/eh_frame/plt/init_array/dynamic/.data`。`.got` 两者均不存在，NOBITS按元数据核对。整个ELF因debug路径不同而不同，不能声称整文件精确复现。
- 编译参数来自能精确复现上述分配节的推定命令，不是历史shell命令原文。固定Clang/LLD22.1.8，`-target aarch64-linux-gnu -shared -fPIC -nostdlib -fno-sanitize=all -fno-stack-protector -O0 -g`，SONAME仍为`libgrm-fbinit9.so`。
- [source-change-verification.json](source-change-verification.json)：baseline/restored源码、两行标准diff、before/after shim指纹、原5点/新4点表、唯一removed site及其它源码字节相等证明；绑定复现和新构建receipt。
- [abi-verification.json](abi-verification.json)：导出符号集合、完整dynsym/import契约、无DT_NEEDED和原unversioned导入均相同。14个原导入由实际父CPIO中的libc/libdl/libgcc_s满足；`__clear_cache`仍走原libgcc_s provider，不混入新provider。
- [member-diff-verification.json](member-diff-verification.json)：仅唯一 `usr/lib/libgrm-fbinit9.so` 记录改变；其它raw records、原顺序和两TRAILER均保持。原appFw该site的4字节、PT_LOAD换算文件位置、原BL解码和新shim四点表也记录在此。
- [shim-build-receipt.json](shim-build-receipt.json) 与 [candidate-build-receipt.json](candidate-build-receipt.json)：精确命令、源/输出/工具链及全部proof指纹。

完整父链保留为 `snapshot(df39ee…da42) → observer(d5732c…54fe) → 295(fd945e…dcef)`，各层CPIO亦有独立SHA。120秒预算、既有按键/捕获序列与平台参数保持，runner负责新schema校验和运行互斥。

**尚无guest内存该site的指令字节readback**；本文件只证明静态输入与最小恢复范围，不宣称运行逐字节完整性。

## 保存与复现

本报告目录仅保存自写源码、diff和JSON凭据，文件指纹在 [files.json](files.json)。`.so/.cpio/对象/cache` 只在被忽略的 `work/fx6-worker-pool-restore-20261107/`。原donor、/tmp源码、既有候选、锁和VM均未改动。

```sh
python3 -B work/fx6-worker-pool-restore-20261107/build_candidate.py
```

builder只做离线构建，不启动VM；每次重建会覆盖工作目录产物并更新manifest时间戳/SHA，不应在候选被运行使用时执行。正式目录是原样源码快照，按上述work布局和固定父候选路径复现。
