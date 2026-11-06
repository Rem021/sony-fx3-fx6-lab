# FX3 r14 低开销 UI gate：仅离线候选

2026-11-04。**完成普通 RAM 精确统计与 N1/N64 镜像节流的交叉编译和有限语义验证；未形成可接入的暂停态权威读取协议，未运行 VM，不可称零帧修复或 runtime-ready。** 本目录只含派生源码、离线 ELF、测试与回执；原 v11、r13、CPIO、DTB、kernel、FX3 平台及默认入口未改。

## 依据与内存门

先核外盘 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，读 `../r13-zero-frame-offline/REPORT.md`（SHA `2f5b27cdbe10a05f00d0a1590b15afe19cd545952ef037d764b312570c6d1e2e`）与 EVIDENCE 映射/成本。r13 的同 root 样本中消费者继续工作，5767 次 gate 判断均跳过，id7/8 为 0；原辅助层有 43470 次 96Q 镜像复制。H1 镜像成本与 H2 原生产/调度失衡仍未区分。

v11 的 `st` 是普通 BSS，`ram` 来自 `memrsv=0x00010000@0x41dc00000:uc` 和 `/dev/mem` `mmap`。当前原 kernel 及映射的 MAIR/PTE 没有足以证明该 `:uc` 区可执行 AArch64 exclusive/atomic RMW 的证据，故**不将权威计数迁到 +0x3000，也不修改 DTB/映射属性**。`__atomic` 继续只作用于普通 RAM；`volatile`/`dmb` 不能替代跨线程原子证明。官方 [GCC `__atomic` 说明](https://gcc.gnu.org/onlinedocs/gcc/_005f_005fatomic-Builtins.html) 指出 relaxed 不提供线程间顺序；[QEMU MTTCG](https://www.qemu.org/docs/master/devel/multi-thread-tcg.html) 则明确多 vCPU 并发。原 `:uc` 别名具体属性和运行性能仍未知。曾考虑 bind 时一次性 pagemap PFN，但它不能证明随后暂停态物理映射仍相同，已从交付源码撤除；[Linux pagemap 文档](https://www.kernel.org/doc/html/latest/admin-guide/mm/pagemap.html) 也说明 PFN 获取受 CAP_SYS_ADMIN 约束。原统计 `st` 的权威数据保留普通 RAM。

## 实现边界

[v11-to-r14.diff](v11-to-r14.diff) 为全部 C 差异。N1/N64 由同一 `fx3-ui-gate-v14.c` 的 `FX3_GATE_PUBLISH_INTERVAL=1/64` 编译，**仅在镜像何时尝试发布上不同**。原 `add/load/save/peak`、96Q 字段前缀、hist/TLS `decision_a18`、事件参数与原返回/errno 路径保留；增加 `object_mismatch` 与 `root_change` 两个末尾 Q，统计总长 98Q=`0x310`，原 bank0 `+0x100..0x410`、bank1 `+0x1100..0x1410` 仍在各自 0x1000 步长内。新字段分别是非 id0/2 事件与当前 root 不同的观察次数、id0/2 对 root 原子替换到不同值的次数；不能用前者单独证明全程单对象。新增 `mirror_visit` 在普通 RAM 计访问；N64 先判断间隔，trylock 成功后再复核，镜像仍用原双 bank、两次 `dmb` 和原 trylock，不等待或更改原业务。初始 bind 镜像照旧；多线程 trylock 忙可跳过，**N−1 滞后只适用于无竞争受控序列，持续竞争及最后无再访可使旧 bank 更旧**。`mirror_skip` 是模式相关诊断数，不在两模式“相等”承诺内。

原装入 60 组 `offsets/words/regs` 三表与旧源码逐字一致，汇编 `fx3-ui-gate-probes-v1.S` SHA=`b82a530c86ad3d37e06ba37828c72942c3c9188d904ed2ab3bee89ebf9f62a1` 与原件相同；原 `cmp w0,#2` 后 signed 分支代码未改。受控 id5 值 0/2/3/`0xffffffff` 的原 C 统计路径已测；**宿主测试的 assembly/loader stub 不等于 guest GPR/SIMD/NZCV 或原分支执行验收**，原运行自测仍待 VM。原 5000ms、timer、优先级、API16、消息和输入合同均未动。`AUDIT.json` 核 0x3000..0x3400 留空供后续独立 nonce 快照协议；本版不占该区、不写 guest 控制位。

## 离线验证与未接线读取

`build_offline.py` 复用原 `fx3-ui-gate-v11-build.json` 所列 Zig cross 工具链和 guest SDK，N1/N64 ELF 均 exit0，`st` 在 ELF BSS 的大小为 `0x310`，动态依赖仅 libc/libdl，undefined 集合与原 v11 完全一致，见 `BUILD.json`。`test_gate_actual.c` 直接编入候选 C（仅将真实 guest 汇编/loader 符号作宿主 stub），固定顺序覆盖 gate/hist/backlog/time、最后发布后仍计数、四 producer 并发、root 换绑、错对象、故意持有 mirror_lock 后不再调用；两模式 native arm64 exit0，公共业务计数逐项相同。此次并发样本 N1 发布 3596 次、N64 发布 94 次，skip 2419/97；这仅是宿主工作量示例，调度造成数值可变，不能称 QEMU 加速。见 `TEST-RESULT.json`。原指令/依赖/范围审计见 `AUDIT.json`。

**宿主权威读取暂不接线。** 原 End stop + query-status paused 后两读同一旧 bank，只证明采样 bank 自身稳定，不能补出末次 probe；全零 OSD 不使旧 bank 变权威。`r14-snapshot-protocol-review/DECISION.md` 提议在原 End 全部读回后、API16 恢复前单独有界 cont/stop 尾段，由下一自然 probe 将普通 RAM 统计复制到 +0x3100 独立不可变槽并 ACK。该尾段需要新身份/nonce、并发单写者、deadline、异常仍 stop/restore/reap 的完整实现与验证；**本版未实现、未写 +0x3000..0x3400、未新增 cont/stop，不能把未来尾段称 End 瞬间或性能观察窗。** 此处停在明确内存/采集门，避免以 PFN/旧 bank 伪造新鲜度。

源与交付哈希分别见 `SOURCE-SHA256SUMS` / `SHA256SUMS`。下一步须另审 nonce 快照协议后才可能构建 CPIO 与安排有界 guest 对照；本轮未授权这些操作。
