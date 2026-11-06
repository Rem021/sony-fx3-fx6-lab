# Stage 288 — Jiritsu 直接 `SET_FILE2` 只读 payload（修正版）

**状态：host-only，尚未放行上机。** 经 DeepSeek 独立复核，旧 `MODE → START → SET_FILE2` 序列与 286/288 的 jbusy 条件都是反的；本目录已按 FX3 `libJiritsu.so` 反汇编修正帧格式、序列与 ELF。当前 payload 仍需自删除/读失败保护等硬化，**不要按旧流程上机**。若“只读”定义为不写任何分区，这条路径本身不成立：`SET_FILE2 op=0` 必然写 p6（`/dev/nflasha6`）的 `/tmp/jiritsu/libJit.so`。

## 0. 结论先行

1. **正确触发序列是直接 `SET_FILE2`**，不需要 `MODE`/`START`：
   - `adj_cmd_set_file2`（`0x9528`）在路径全串等于 `/tmp/jiritsu/libJit.so` 时检查 `/tmp/jbusy`：
     - `0x976c..0x977c`：`sys_file_chk_exist("/tmp/jbusy")`；**存在（stat=0）→ `0x9944` 状态 `0x10000011`，一个字节都不写**；
     - **不存在（ENOENT）→ 继续写文件，`0x9908 dlopen(path,1)`，`0x9928 dlclose`**。
   - `stage230` 的真机报告与公开 A7C II 工具同样记录“`/tmp/jbusy` 存在时拒绝写入”，与上述分支一致。
2. **命令帧必须带前缀**：
   - `SET_FILE_PATH`：`00 + path + 00`（`0x8a1c` 要求首字节 0；`0x8a4c` 从 data+1 拷 size-1）。
   - `SET_FILE2`：`00 ff 00 + file`（`0x95a4` 拒绝 selector 2；`0x96b0/0x9890` 从 data+3 写 size-3）。
   - `GET_FILE2`：`00 ff 00`（`0x9efc` 把 selector 与 ~2 相与；0/2 被拒，0xFF 走当前路径）。
3. **ELF 动态表已修**：`DT_SYMTAB=0x2070`、`DT_STRTAB=0x2088`、`DT_HASH=0x2089`，全部落在 PT_LOAD 内；`DT_HASH` 处实际是 `(1,1,0,0)`。新 SO SHA256 `05000a0ecceaa5004385b71fbeb2b15859bda7418e227a3d90238da31bc4cd7a`。
4. **仍不能上机**：payload 还没有自删除、read 失败会截断旧 `sector0.bin`、`/dev/nflasha` 裸节点未证实、Jiritsu 进程为 euid=0。先修再申请只读会话。

## 1. 旧流程的四处 P0（已修正）

| P0 | 旧写法 | 二进制事实 |
|---|---|---|
| jbusy 条件反了 | “jbusy 存在才 dlopen” | `0x977c cbz w0,0x9944`：存在→`0x10000011`；不存在→写+dlopen |
| 帧缺前缀 | `path+00`、`00+file`、`00` | `00+path+00`、`00 ff 00+file`、`00 ff 00` |
| ELF 表越界 | `DT_*` 指向 0x2100/0x2120/0x2130，文件只到 0x2099 | 表实际在 0x2070/0x2088/0x2089；`DT_HASH` 原读 `(0,0,0,0)` |
| MODE/START 多余 | 先 MODE 再 START 等 jbusy | `cmd_start` 只服务 `jit_thread`；内联 `dlopen` 在 `SET_FILE2` 内。`cmd_mode` 成功状态是 4，写的是 `" TE"`（`%sE`），不是 `" T"` |

## 2. 正确的最小序列

```text
（可选预检）SET_FILE_PATH(/tmp/jiritsu/../../tmp/jbusy) -> GET_FILE2；若 status != 0x11 则停止
SET_FILE_PATH(/tmp/jiritsu/libJit.so)
SET_FILE2(00 ff 00 + libJit_test.so)     ; jbusy 必须不存在；写 p6 后内联 dlopen
SET_FILE_PATH(/tmp/jiritsu/sector0.bin)
GET_FILE2(00 ff 00)                      ; 4B status + 512B
```

不使用 `MODE`（1）、`START`（4）、`FORMAT`（3）、`MOUNT`（2）；不创建 jmode/jbusy；不发送 `edisx`/`uc_mkfs`。

## 3. 主机侧产物与测试

| 文件 | 说明 |
|---|---|
| `jiritsu_wire.py` | select/write/read 帧，`00`/`00 ff 00` 前缀，selector 2 拒绝 |
| `test_jiritsu_wire.py` | 13 个正反例 PASS；SO SHA 新值；SET_FILE2 线包 8,364B |
| `fake_jiritsu_camera.py` | 模拟 jbusy 存在→`0x10000011`、不存在→写+构造器；无 MODE/START |
| `test_session_flow.py` | 最小路径 PASS；jbusy 反例、selector 2、错误路径、GET absent 全部 PASS |
| `payload/libJit_test.so` | 8,345B，SHA `05000a0e...`；只读 `/dev/nflasha` 512B → `/tmp/jiritsu/sector0.bin` |
| `payload/jit_payload.c` / `.o` / `build_jit_so.py` | 源码/对象/可复现重建；ELF 动态表已修 |

离线测试：

```sh
python3 -B test_jiritsu_wire.py
python3 -B test_session_flow.py
```

## 4. payload 仍缺的硬化（上机前必须）

1. **自删除**：构造函数开头 `unlinkat(AT_FDCWD, "/tmp/jiritsu/libJit.so", 0)`；`dlopen` 已映射，删除安全（stage230 公开载荷先例）。否则 p6 生产 JIT 路径会留下 root-owned SO。
2. **read 失败不截断**：`n != 512` 直接返回，不 `open(..., O_TRUNC)`；当前代码会留下 0 字节 `sector0.bin`，无法区分“读失败”和“成功读 0”。
3. **输出语义**：文件存在且正好 512B 才代表成功；建议加一个固定 8B 标记/长度头，或 host 侧严格校验。
4. **`/dev/nflasha` 裸节点**：提取物里只见到 `/dev/nflasha6` 的引用；整设备节点是否存在/可读是 `unknown`。若不存在，payload 静默失败。
5. **p6 写入是持久的**：`SET_FILE2` 写 `/tmp/jiritsu/libJit.so`（p6），payload 再写 `sector0.bin`（p6）。如果“只读”要求零分区写，这条路径不可试；只能改用 `op=0xFF` RAM 槽验证线协议，但不会执行 SO。
6. **64KB 页/glibc 版本**：当前 ELF 两段 `p_align=0x1000`；若内核 64KB 页，段权限合并行为 `unknown`。提取物只有 `ld-2.25.so`，Sony 补丁未知。

## 5. 上机前/中/后判据

**上机前（host-only）**
- 帧逐字节：`00+path+00`、`00 ff 00+SO`、`00 ff 00`；不符即停。
- Python 校验 SO：`DT_HASH` 处 `(1,1,0,0)`；三个指针均在 PT_LOAD 内；不符即停。
- 预检 `/tmp/jbusy`：`GET_FILE2` 返回 `0x11` 才继续；存在则停，不强行删。
- 确认 `/tmp/jiritsu/libJit.so` 不存在或已备份；来源不明不覆盖。

**会话中（任一即停）**
- `SET_FILE2` 非 0：`0x10000011` jbusy 在；`0x10000201` 帧/路径/selector 错；`0x10000000` 已写但 dlopen 失败；`0x10000004` 挂载失败；`0x1000000F` p6 空间不足。
- `GET_FILE2` 不是 512B，或 magic 不是 `8246`/`2.00`，或 n≠30，或 p1 不是 `0x80/0xBF80`。
- USB 超时、相机屏幕异常、Jiritsu 进程重启、`/tmp/jbusy` 意外出现。

**会话后**
- 确认 `libJit.so` 已自删/清理；`sector0.bin` 按需保留；`/tmp/jbusy` 不存在。
- 清理失败即停，不重发第二次 `SET_FILE2`。

## 6. 与全系统主线的衔接

Sector 0 读回只是**入口验证**，不代替：
- 全分区备份（Sector 0 + p1/p2/p3/p5/p6/p7/p8/p12/p13/p15/p18/p23/p30 + SPI NOR）；
- p1-only 单次引导（保持 p3/p2/p8/NOR 不动）；
- `edisx`/`uc_mkfs` 重分区与 FX6 镜像写入。

在这些完成前，不执行任何持久刷写。当前主机 C 传输仍只有 `read0`/STOP；直接 `SET_FILE2` 需要新增通用 AdjustControl 发送器与 fake IOKit 回归，这是下一段工作。

## 关联证据

- [Stage 286 线协议](../stage286-post-communication05-session-and-wire-envelope-audit/README.md)（其中 jbusy/op=0 帧描述已被本目录修正）
- [Stage 230 直接加载分支](../stage230-constructor-child-entry-portability/README.md) 与公开 `libjit_requests.py`
- [FX6 全系统 → FX3 兼容矩阵](../../../reports/2026-11-03-fx6-full-system-to-fx3/README.md)
- FX3 `libJiritsu.so`：`work/sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so`

---

**范围**：本目录只证明主机侧编解码、离线状态机与静态 payload；不把任何静态推断写成真机结果。修正后的第一次真机仍只做 Sector 0 读回，且必须先接受 p6 写入与 Jiritsu 进程风险。
