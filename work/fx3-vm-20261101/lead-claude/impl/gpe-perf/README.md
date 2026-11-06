# GPE 性能候选：backend v9 / adapter v26

**`python3 -B build_and_test.py` 退出 0；v8/v9 逐字节一致、ASan/UBSan 通过，AArch64 O2 共享库已生成。** 仅写本目录，未修改 runtime、STATE 或 CPIO，未启动 QEMU。此处证明宿主软件结果与 v8 一致；5000ms 原接收期限能否满足，仍须由运行链验证。

## 复跑与文件入口

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-claude/impl/gpe-perf
python3 -B build_and_test.py
```

写入前核对卷 UUID；复用系统 clang、既有 Zig/guest SDK 与审计 venv（Unicorn/Capstone/pyelftools），无安装依赖、无网络构建。Zig 缓存和 TMPDIR 都位于本目录。

- [构建及全部测试命令](build/commands.json) · [总回执](build/test.json) · [正确性](build/correctness.json) · [未改语义的结构核对](build/semantic-preservation.json) · [来源与源码 SHA](build/provenance.json)。任何构建/运行失败使脚本非零退出。
- [v8 冻结基准](fx3-gpe-backend-v8.c) / [头文件](fx3-gpe-backend-v8.h) 原样来自 runtime；SHA `b2fcf092426c4919f5c74a130447348d7e08edcb34302faaa470802f625fd220`。不是复制整个 runtime 或仓库。
- [backend v9](fx3-gpe-backend-v9.c) / [头文件](fx3-gpe-backend-v9.h) / [光栅循环](raster-v9.inc) / [常量表](tables-v9.inc)。[v8/v9 测试](check_perf.c) 与 [宿主回放向量](build/vectors.json)。
- [adapter v26](fx3-gpe-observe-v26-perf.c) / [映射及回调缓存](cache-v26.inc) / [资源生命周期](resource-v26.inc) / [观测开关](texture-v26.inc)；[make_adapter.py](make_adapter.py) 从 SHA 固定的 v25 生成。
- [正式候选 .so](fx3-gpe-observe-v26-perf.so) · [交叉编译参数](build/cross-build.json) · [ELF/SONAME/依赖/导出检查](build/elf-verification.json)。目标 `aarch64-linux-gnu.2.25`、`-O2 -mcpu=generic -mno-outline-atomics`，沿用现有 guest libc/libdl/libpthread/loader 链接配置，仅需基线 AArch64/Advanced SIMD，不依赖额外扩展。

## v9 保持的合同与优化

planner、坐标/clip/格式/flags 准入、extent/epoch、租约、全源/目标 span 预检、包络重叠拒绝、批次、事件、callback→同步 status 顺序及 fence 与 v8 原字节一致；header 仅换 include guard，ABI 不变。只替换所有校验通过后的像素循环及其纯数学辅助函数。无全局可变初始化、堆分配、IO 或线程操作。

1. K255 覆写按行 memcpy；Fill 首行 memset/打包填充后复用行。K255 混合的整行不透明源经实际 alpha 扫描后 memcpy；透明源及 K0 保持目标。nearest 覆写重复采样同一源行时复用上一目标行。
2. `R255(n)=floor((n+127)/255)` 在 `0<=n<=65025` 改为 `t=n+128; (t+(t>>8))>>8`，全范围穷举验证。fmt0 的通道、alpha、最终 q4 使用 69,888B 不可变表，按 v8 的逐阶段舍入生成；没有改成近似 /256，也没有改变 Fill 原高4bit截断。
3. fmt0/fmt1 专用内联读写；每像素不再调用通用函数。nearest 用精确商/余数递推，除法只在命令开始，repeat 用原 mask；裁剪偏移、翻转及 center/edge 采样与 v8 一致。行和像素字节索引用宽整数。

原近似模型保持 `straight_over_v1`、fmt2 A8 着色、nearest_v1/v2、repeat_mask_v1；**不是 Sony 芯片像素 oracle**。公式和边界来自 [fmt2 审计](../../audits/gpe-fmt2-resource-extents/README.md)、[离屏审计](../../audits/offscreen-subblock/README.md)、[P3 审计](../../audits/gpe-blend-p3/README.md) 与现行 v8。

## v26 固定开销

- 已登记的 native screen 用原对象字段 + epoch 权威复核，绘制期跳过辅助 procfs；登记时保留 proc 辅助观测。无已登记 owner 时保留原完整 proc 解析与有界重试，未知对象不因缓存放行。
- 在 lifecycle_lock 内按 `(object, epoch, physical base, bytes, protection)` 复用父 extent 映射，最多64项；close/reopen、epoch 改变、字段失配均使旧映射失效并 munmap。容量满或没有可信对象/epoch 时回退临时映射。源映射覆盖登记父区间，但 backend 仍只注册并校验原 crop 包络，没有扩大像素准入。
- 生产默认 `GPE26_TEXTURE_OBSERVE=0`：不复制纹理、不做 SHA/直方图；诊断构建可显式 `-DGPE26_TEXTURE_OBSERVE=1` 恢复冻结 v25 观测。现有命令/拒绝/完成标记保留。
- 提供可选 executable-token 缓存及 `fx3_gpe_callback_cache_invalidate26()`；**生产默认 `GPE26_CALLBACK_CACHE=0`，保留每次原 maps 校验**。启用前，集成方必须覆盖并串行化所有 dlclose、munmap、mprotect 及直接 syscall 的代码映射变化，再调用失效 API；当前只有 dlopen 自动失效，未伪称已证明完整模块生命周期。默认候选不依赖这个额外假设。

这些缓存不补齐原先未覆盖的 compaction、bitmap 子块绑定、queued ABA；原标记继续保留。首次映射失败仍失败，缓存命中不再重做 mmap/munmap；不声称消除原 syscall 后验失败或提供像素回滚。

## 正确性与真实输入

2,058 个完整历史参数来自 AP89/AP90/AP97/AP101/AP104，另有10个明确标注的640×480分类向量、1,200个随机几何组合、不透明源专例和边界/短 extent/过期及 retiring 租约反例；1,513,602 项数学比较、总计 1,560,681 项检查。完整目标+guards 累计比较 2,470,763,765B，源、plan、context、租约、事件与回调记录一致；896 项拒绝零写入检查通过。backend 与两个 adapter 的 ASan/UBSan 均无诊断。

[原参数及 run/LF 行号](build/vectors.json)、[各轮命令统计与日志 SHA](build/corpus-statistics.json)、[LDEC 真实纹理清单及 SHA](build/textures.json) 均可复核。每次重新解码12份真实 LDEC 样例，逐字节核对已有 raw；样例来自原 UX 资源。历史 buffer 的原始运行前像素没有完整保存，故回放使用这些真实资源字节填充/重复构造源面；**未证明样例与每条运行 bitmap 的 ID 绑定**，也不把它当原厂整帧复现。保留原始56B/144B body，计时仅按适配器惯例清完成字段为 async，避免测传输 hook。

## 宿主640×480分类基准

使用真实 LDEC 内容、fmt0 目标；CLOCK_MONOTONIC，v8/v9 交错执行，各7组×12次取中位数，含 submit/plan/跨度检查，排除 setup/reset。新增全幅几何是分类覆盖，不冒充历史原参数。

| 类别 | v8 μs | v9 μs | 加速 |
|---|---:|---:|---:|
| fill_replace | 1077.42 | 13.25 | 81.31× |
| fill_blend_K128 | 14287.08 | 2760.42 | 5.18× |
| blit_replace | 3936.58 | 17.33 | 227.11× |
| blit_blend_K255 | 5742.75 | 578.42 | 9.93× |
| blit_blend_K65 | 6003.42 | 690.75 | 8.69× |
| nearest_center | 1952.25 | 474.58 | 4.11× |
| nearest_edge_blend | 7901.58 | 902.17 | 8.76× |
| repeat_tile | 7773.42 | 673.58 | 11.54× |
| fmt2_A8_K255 | 2831.83 | 1197.83 | 2.36× |
| fmt2_A8_K128 | 7504.58 | 925.33 | 8.11× |

原始几何另测每个实见类别的最大已准入向量，见 [完整结果](build/historical-performance.json)。类别中的 K 以下表实际参数为准：

| 原参数类别 | run / seq | K | v8 μs | v9 μs | 加速 |
|---|---|---:|---:|---:|---:|
| fill_replace | ap97r2alpha600-cd3c48f7 / 0 | 255 | 757.00 | 12.42 | 60.97× |
| fill_blend_K255 | ap97r2alpha600-cd3c48f7 / 1 | 255 | 3817.83 | 13.67 | 279.35× |
| blit_blend_K255 | ap89r2replay-a55f292d / 72 | 255 | 4150.75 | 434.83 | 9.55× |
| blit_blend_K65 | ap97r2alpha600-cd3c48f7 / 807 | 65 | 120.33 | 4.67 | 25.79× |
| nearest_edge_blend | ap101r4tile600-be9996d0 / 968 | 255 | 1770.75 | 317.33 | 5.58× |
| repeat_tile | ap101r3emptyclip600-49610a67 / 782 | 255 | 10.17 | 1.92 | 5.30× |
| fmt2_A8_K255 | ap97r2alpha600-cd3c48f7 / 74 | 255 | 145.67 | 51.25 | 2.84× |
| fmt2_A8_K128 | ap101r3emptyclip600-49610a67 / 610 | 128 | 64.08 | 22.83 | 2.81× |

这批保存参数中未找到可在本640×480目标上计时的纯 blit 覆写与 nearest-center 原向量，它们由上面的合成分类覆盖。原 Fill 混合样例 K255 且源不透明，因而可退化为覆写；其高加速不能代表一般半透明混合。

## 适配层宿主基准

actual v25/v26 command 函数经过同一 mock 的350行 procfs、物理映射、pread、SendDrawComp；真实纹理观测 SHA 由 v25 原代码执行。每场景60条命令、5次进程取中位数；四场景最终目标 digest 相同，另测 callback→status、非法 callback/过期 owner 零写、close/重开 epoch 失效。

| 场景 | v25 μs/条 | v26 μs/条 | 宿主加速 |
|---|---:|---:|---:|
| fill16x2 | 868.550 | 0.967 | 898.19× |
| blit16x2 | 746.233 | 1.400 | 533.02× |
| blit1x2_to441x2 | 753.367 | 3.183 | 236.68× |
| blit640x384 | 18463.133 | 365.167 | 50.56× |

每60条命令，v25 要360次 proc 文件打开；v26 已登记 owner 为0。小 blit 的物理 mmap/munmap 从120/120降为首次1/0，后续复用；资源 close 后验证真实撤销。日志格式化/内核 MMU/TLB 没有在 mock 中测量。[报告](build/adapter-performance.json) 附 syscall 数量和假设每次额外1ms的敏感性计算，**该1ms不是实测或校准的TCG延迟**。

## AArch64 / TCG 工作量估算

[离线报告](build/tcg-estimate.json) 对 O2 generic AArch64 ELF 用 Unicorn 回放64×4缩小向量；所有目标输出相同，计数器确认函数正常返回。无 QEMU。memcpy/memset 为独立 C 自动向量化模型，不是 guest glibc；给出总指令比和保守权重敏感性（scalar1、load/store2、SIMD4、divide8）。

| 类别 | v8/v9 指令量比 | 加权工作量比 |
|---|---:|---:|
| fill_replace | 3.40× | 3.31× |
| fill_blend_K128 | 3.99× | 3.33× |
| blit_replace | 5.26× | 5.50× |
| blit_blend_K255 | 4.27× | 3.89× |
| blit_blend_K65 | 3.59× | 3.32× |
| nearest_center | 2.89× | 3.06× |
| nearest_edge_blend | 4.06× | 3.79× |
| repeat_tile | 3.66× | 3.33× |
| fmt2_A8_K255 | 2.55× | 3.66× |
| fmt2_A8_K128 | 2.55× | 3.66× |

这只是预计减少的软件工作量，未包含 TCG 翻译、调度、页表或 syscall；**不能换算为44.7秒必降到某值，也不能宣称5000ms验收已通过**。QEMU 官方说明也明确指令数与实际性能未必相关：[TCG icount](https://www.qemu.org/docs/master/devel/tcg-icount.html)、[Invocation](https://www.qemu.org/docs/master/system/invocation.html)。sanitizer 参数按 [Clang ASan](https://clang.llvm.org/docs/AddressSanitizer.html) / [UBSan](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html) 官方说明核对（2026-11-02）。

## 给运行链持有者的集成步骤（本工人未执行）

1. 在本目录复跑 `python3 -B build_and_test.py`，核对 `build/test.json`、`cross-build.json` 和 ELF 回执。当前候选 SHA256：`30667f76ccfa3f0b9b4834b1fbce725a76683ccd775615ed66955d49200d7ba4`。
2. 只在新候选 CPIO 中，把成员 `simulation/fx3-gpe-observe-v7.so` 的内容替换为本目录 v26 `.so`，保持原固定成员名与现有 preload 顺序；不要同时 preload 两个 GPE 版本。保留原 capid 外层 caller guard 与轻量观察库顺序。
3. 默认生产开关保持纹理观测关闭、callback cache关闭；没有新的运行环境变量。若另建诊断版，将 `-DGPE26_TEXTURE_OBSERVE=1` 加入本目录交叉编译命令，并为其单独记录新 SHA；不要覆盖生产验收回执。
4. Lead 持有既有运行锁，核对 CPIO 成员、DTB、SHA、STATE 后执行运行；应见 `adapter=v26_perf backend=v9 object_authoritative_no_draw_proc=1 mapping_cache=object_epoch`，登记、释放及旧拒绝标记仍可审阅。
5. 重走语言弹窗，逐批测原 ReceiveDrawComp 开始→完成投递是否小于5000ms，并确认没有 timeout/unfetched、断言或完成重复；最终物理面与菜单截图另行验收。缓存后不应再出现每条绘制的 proc 读取/物理映射；用关闭重开/代次变化核对撤销，完整寿命与真实 kernel/mm 行为仍属于 guest 门。
