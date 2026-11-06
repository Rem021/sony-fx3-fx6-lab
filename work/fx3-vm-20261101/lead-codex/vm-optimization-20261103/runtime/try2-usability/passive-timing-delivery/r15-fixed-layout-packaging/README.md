# FX3 固定 CPIO 槽位打包工具（离线）

2026-11-04。**工具、r14 体积样本和 synthetic 验证已完成；没有生成真实 CPIO，没有集成最终 r15，也没有运行 VM。** 本目录不是新运行入口，不修改 runner 硬编码 pin。最终 r15 nonce 协议由另一个任务负责，本工具不实现或验证该协议。

入口：[REPORT.md](REPORT.md)、[MANIFEST.json](MANIFEST.json)、[fixed_layout.py](fixed_layout.py)、[test_fixed_layout.py](test_fixed_layout.py)。所有生成物仅在本目录。旧 failed 证据、原 r14、原 r3、DTB/kernel/platform、入口、根 README/ledger 均保留。

## 固定边界

- 固定 r3 `candidate.json` SHA：`a8fd7e81e00353f8dbd5dc579f6d440f28ecd083fc15d8e1335899c44b108518`。
- 固定 `guest.cpio`：453,213,884 B，SHA `31ce79e9284ff45f227d2cc981faf85947d6f2e70e8ff60b447b671b26107b83`。
- 唯一许可跨度：`simulation/fx3-ui-gate-v1.so` 的 payload `[451339648,451398504)`，58,856 B；header 从 451339508 开始，mode `0100755`，standalone regular，newc `070701`。
- 原槽位 SHA：`54eeed923a6412cd2c6743f6e8c968d1ede71b92aa79aca4575868ebccc4a9ec`。
- 原 DTB SHA：`5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b`。写出模式引用原 DTB；不复制、不重编码，不改 `initrd-end`。
- 整个 header、名称、顺序、size、mode、所有 payload offset、padding、trailer 和总长原样保留。槽位内容仅为审计过的辅助 SO + 零填充，其余每字节必须相同。Sony ELF 不参与替换或 strip。

`plan` 本轮只读取真实 CPIO 的 header/name、seek 到下一成员，读取目标 58,856 B；不重算整幅 CPIO SHA。记录明确标为 `not_rehashed_in_seek_only_plan; required_before_write`，不能用该计划宣称当前全镜像身份已完整复核。`write` 在创建目标之前完整核原镜像 SHA；复制中再次计算源 SHA，写后全量比较许可跨度外每字节并核槽位内容、总长、完整索引和原 DTB。

## ELF 体积处理与审计

指定 Zig `objcopy --strip-debug` 对实际 ELF 返回 `error: unimplemented`，留下 0 B 工件；见 `OBJCOPY-FAILED.json`。工具链源码 `lib/compiler/objcopy.zig:197-207` 的 ELF 分支直接拒绝。失败文件没有覆盖或移除。

协调端在 `msg_b4a35376625d` 明确批准替代：使用冻结 `BUILD.json` 原命令，仅新增 `-Wl,--strip-debug` 并更换输出。该链接器同时移除非运行时 `.symtab/.strtab`；这项差异被明确接受，不能再称“仅去 debug 节”。`prepare_r14_samples.py` 已各执行一次 N1/N64，完整带 debug 原 ELF 永久保留，固定 hash 不变。禁止 `--strip-all`；最终 release 必须绑定原 build、源码 manifest、执行回执、输入文件与 ELF SHA。

`audit_elf` 独立解析 ELF64 LE/AArch64 ET_DYN，比较全部程序头、全部 SHF_ALLOC 节的地址/大小/flags/type/offset/align/entsize 和原始数据（NOBITS 单列）、动态依赖/SONAME/search paths、动态导出与未定义符号。普通非分配节也检查；只许可删除 debug 节及经批准的静态符号节。ELF 头只允许 `e_shoff/e_shnum/e_shstrndx` 改变。逐 PT_LOAD 比较只容许这些头字段覆盖的字节变化，记录每处 offset；**不会宣称整个 PT_LOAD 逐字相同**。

`plan` 与 `write` 都重新审计 ELF 和构建来源，不接受单独一份 `passed:true` 的审计回执作授权。来源回执本身不是数字签名或执行证明；操作者仍须审查最终 release 及其冻结来源。动态符号相等和 ELF 语义检查不等于实际 guest 运行验收。

## 本轮结果

| r14 样本 | 原 debug ELF | 链接去调试 ELF | 补零 B | strip ELF SHA |
|---|---:|---:|---:|---|
| N1 | 60,544 | 20,400 | 38,456 | `f95d91c1c5f3ca41303edf0df9fa25b574f0c70f903f163b8aaef36c36a4b1b4` |
| N64 | 61,624 | 20,576 | 38,280 | `54092d471ade3a599adbd563e75cb4c140ccc34b8e7245f65aeeba42aa6aa1fc` |

两份样本的 19 个分配节、全部程序头、5 个动态导出、14 个未定义符号一致。首个 PT_LOAD 仅文件 offset 40/41/60/62 不同。具体数据在 `samples/*-ELF-AUDIT.json`，原/strip/padded slot 三个 SHA 在 `dry-run-N*/plan.json`。真实索引为 1,140 个非 trailer 成员，trailer 精确结束于 EOF，无尾 padding。

最终 `TEST-REVIEW.log` / `test-artifacts-review/RESULT.json`：40/40，通过真实生产 Python 函数验证 synthetic newc/ELF 的成功路径、拒绝路径、未来 r15 版本写出门、固定长度/区间外比较和失败保留。测试的 `guest.cpio` 全是几 KiB synthetic fixture；其构建元数据也是明确标记的 fixture，并非实际交叉编译。实际 r14 样本另有执行过的 Zig 命令及来源回执。早期 34/38 项回执保留，最终以 40 项为准。

## 后续调用（仅供协调端在最终 r15 冻结后执行）

以下均需绝对路径；`PKG` 指本目录。外盘 UUID 必须匹配 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。所有输入和现有父目录不能是 symlink；输出目录必须不存在，父目录必须已存在，必须在 Mac 项目内，不允许写入冻结 `v25-*` 候选或原 r3。不会自动创建回退目录、转存其他卷或覆盖历史。

1. 准备最终 r15 完整 debug ELF、按上述唯一 flag 产生的小 ELF 和人工审查的 release JSON。两者 SONAME 必须分别对应 `fx3-ui-gate-v15-n1.so` / `...-n64.so`；helper version、variant、SHA 必须一致。如最终构建 receipt schema 不同，先审查适配，不绕过门。

2. release JSON 使用 `samples/N1-release.json` 的结构，替换最终冻结值：

```json
{
  "schema": "fx3-fixed-layout-release/v1",
  "helper_version": "r15",
  "variant": "N1",
  "soname": "fx3-ui-gate-v15-n1.so",
  "raw_sha256": "最终debug ELF的SHA",
  "stripped_sha256": "最终小ELF的SHA",
  "provenance": {
    "raw_build_manifest": {"path": "绝对路径/BUILD.json", "sha256": "已审查SHA"},
    "source_manifest": {"path": "绝对路径/SOURCE-SHA256SUMS", "sha256": "已审查SHA"},
    "strip_build_receipt": {"path": "绝对路径/strip-build.json", "sha256": "已审查SHA"}
  },
  "diagnostic_contract": {"说明": "引用最终另行审查冻结的r15诊断合同，不由本工具发明"}
}
```

原 `BUILD.json` 的 `variants.N1/N64` 应含 `command/exit/sha256`；strip receipt 的 `schema=fx3-linker-strip-build/v1`、`command/original_command/exit/raw_sha256/stripped_sha256/command_input_hashes` 格式参照 `samples/N1-build.json`。程序要求命令只新增一个 `-Wl,--strip-debug` 并替换唯一 `-o` 输出；源码 manifest 和所有绝对路径编译输入（含工具链、SDK 库）逐 SHA 复核。

3. 先写可审查计划和索引，不生成 CPIO：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$PKG/fixed_layout.py" plan \
  --raw-helper /绝对路径/最终debug.so \
  --helper /绝对路径/最终linker-strip.so \
  --release-contract /绝对路径/最终release.json \
  --report-dir /绝对路径/全新计划目录
```

4. 计划和最终 r15 SHA 经审查后，另行授权调用显式写出模式（**本轮没有执行**）：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 "$PKG/fixed_layout.py" write \
  --plan /绝对路径/全新计划目录/plan.json \
  --output-dir /绝对路径/全新候选目录 \
  --acknowledge-real-cpio-output REVIEWED_R15_FIXED_SLOT
```

r14 release 只能 dry-run，生产写出门拒绝 r14。CLI 无替换原 pins/base/UUID 的参数。工具没有默认写出动作，不会执行 strip、编译、启动 VM 或更新 runner pin。

5. 仅 `COMPLETE.json` 存在且 `state=complete` 才表示打包与静态验证通过。初始 `INCOMPLETE.json` 作为历史起始标记保留，成功回执明确 supersede 它；失败则保留 `guest.cpio`（可能不完整）、`INCOMPLETE.json` 和尽力写入的 `FAILED.json`，不自动清除。无 `COMPLETE.json` 一律不能使用。文件系统完全不可写时失败回执本身也可能无法落盘，stderr/异常仍表示失败。

成功时自动产生新 `candidate.json`，**除 `initrd.path/sha256` 和新增 `fixed_layout_diagnostic_contract` 外，r3 所有字段逐项相同，包括原 DTB 路径/SHA 与既有合同**。不生成新的 DTB，不宣称 runtime-ready、已部署、VM 通过或 FX6 可用。

## 复核与依据

`SHA256SUMS` 覆盖脚本、文档、样本、计划和所有 retained 测试证据；`HASH-CHECK.txt` 为校验回执。复测只能指定新的 `test-artifacts-名字`，不会删除或覆盖旧测试目录：

```sh
PYTHONDONTWRITEBYTECODE=1 python3 test_fixed_layout.py --evidence-name test-artifacts-check2
```

参数中的复核名使用 ASCII 字母数字，例如 `test-artifacts-check2`。无需为当前已通过样本重复运行。

读取日期 2026-11-04：[Linux initramfs buffer format](https://www.kernel.org/doc/html/latest/driver-api/early-userspace/buffer-format.html) 定义 newc header、名称和 4 字节对齐；[ELF gABI 4.2 sections](https://gabi.xinuos.com/v42/elf/03-sheader.html) 定义 SHF_ALLOC 的内存含义。本工具有意只接受当前固定原件的单一 `070701`、trailer 正好 EOF 布局；这不是通用 initramfs 解包器或重打包器。
