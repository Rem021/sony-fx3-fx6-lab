# r30 启动观测候选

**离线候选通过；底层 backlog 未修复，真实启动/八步菜单仍待单独验收。** 本目录基于冻结 r28，只补宿主证据；没有启动 VM、Start、浏览器或服务，没有部署。r28 原 180 秒/0 键失败保持不变。

## 改动与证据边界

新增 `startup_observation.py`，本地派生 r21 的 `trial_ring_cached.py / trial_log_v4_mss.py`，修改 r28 runner、prepare、preflight 和 return adapter 的新 CORE pin；具体见 [MINIMAL.diff](MINIMAL.diff)。33 项生产文件与 r28 逐字节相同，36 项 CORE、41 项生产文件均重新冻结；没有复制整个 runtime 或历史大日志。

- Header 沿用每次原 `pmemsave`，记录 request id 前后、host monotonic_ns 前后、原长度门所见文件长度、可用16Q、拒绝类别、serial 消费 offset 和 startup/cleanup 阶段。QMP 异常仍抛原异常，错误响应仍走原空结果；异常时不读取旧导出文件。原错误长度准入仍返回空，只允许对同一宿主导出文件额外读取最多128B诊断前缀，前缀不进入原 reader。`valid_positive` 仅表示全局头有正序号，槽/FNV/像素资格仍由原代码决定。
- Marker 使用原 `f.read()` 的新增 **bytes** 和真实起点，只保留最长 token−1 的尾巴及14项白名单首次命中。不从 KEEP 返回字符串或重新 encode 后长度推断偏移，不增加 serial 文件读取/历史扫描。首次完整 literal token 收到与后续 LF 收到分别记录；不把 token 当完整语义事件或 guest 发生时刻。长未终止行不会扩大观察缓存。
- 原 ready BoolOp 的每个操作数只加返回**同一原值**的观察调用，保持短路、原表达式和原控制时钟调用；未求值为 `not_evaluated`。记录当时最后 screen 的 host 观察时间、serial offset 与当前已验证 ring 身份，绝不把最终 marker 集倒填为早期 ready。
- Header 最近48次变化、ready最近32次变化、阶段最近8次变化；各流固定保留初始/末次及前32种状态，另有明确 eviction/omission 计数。header 的有限类别按阶段保留首次，覆盖 invalid→valid、seq0→positive 及 cleanup 首帧。只在原回收和锁释放检查之后尝试一次≤256KiB文件替换，无每 poll 写盘、无 fsync；普通异常和 KeyboardInterrupt 的 guard-finally 仍有安全写盘兜底，失败不影响原健康或退出。原件没有任何写入。

详见 [CONTRACT.md](CONTRACT.md)。诊断时间属于 host 收到/执行点，不提供 guest/server/browser 原子准入或 compositor 时刻。

## 离线验证

[OFFLINE-RESULT.json](evidence/OFFLINE-RESULT.json) 的 **43项通过**：实际旧/新 reader 的 short、错误magic/version、seq0/positive/重复、坏槽、QMP异常/错误响应、异常后旧文件及宿主读取异常；实际 monitor 在 UTF8/无效字节/跨chunk/无LF长行及 r26/r26b/r28 原日志回放中，返回、selected、failure、date99和读取区间均等价，首次白名单偏移匹配 raw oracle。历史回放的到达时刻是明确的 fixture 值，**没有重造 r28 未留存的早期 header 或 host 收到时间**。

全部13个 ready 条件分别覆盖 true/false/not_evaluated，原条件异常保留；实际 runner 启动循环源码片段与 execute_runner 包装器，在受控 QMP/时间/像素 fixture 中对照 ready、异常、cleanup-only首帧、普通错误及 KeyboardInterrupt。QMP 调用序列、原 monotonic/sleep 调度、ready/exit/异常结果一致；没有运行 runner main 或真实 native/视觉测试。首次测试仅因 fixture 目录重名中止，原失败 stderr 保留；修正目录名后的通过结果及后续补齐的回执均保留。

[结构化检查](evidence/STRUCTURAL-AND-COST.json) 证明：移除观察增量后整个 runner 功能 AST 等于 r28，monitor 原功能 AST 等于 r21，原 ring poll/validate_slot/evidence AST 未变。截断测试3001次header和1024次ready变化后，实际文件72318B≤262144B，eviction/omission显式记录；写盘/时钟故障没有跳过原 guard 清理。

实际 [prepare/preflight](evidence/prepared-6540dfe4e72f/PREFLIGHT-RESULT.json) 通过，未执行 launch_prepare/start_and_wait/operate main；干净子进程 import-only 证明三项新观察模块确实来自本 r30，而 QMP/input/resource guard 来自冻结 r21。新 return adapter 实际 import 的 FROZEN/OPERATE 指向 r30，CORE pin匹配；其 AST 仅 pin常量不同，三个JS返回模块与r28字节相同。PAGE canonical仍为 `852c83d6…6acfa55b`，导航计划仍为 `4a695e1a…71cff02f`，r28 5秒首观察、独立pin/confirm、20秒alarm与实时server门未变，见 [最终绑定回执](evidence/FINAL-VERIFICATION.json)。

## 开销、输入与剩余工作

本机 callback 微测三次中位：header约 **0.860µs/次**，短路ready约 **2.057µs/次**、13项全求值约 **3.138µs/次**；5.126MB原日志仅新增marker扫描约 **7.15–7.80ms/轮**。这是新回调测量，未含 QMP、原解析、错误长度的宿主128B读取或最终写盘，不能当作 VM 性能保证。控制/等待策略等价不等于 wall-time 完全相同，观察开销仍可能扰动调度；突然杀死宿主会丢失尚未落盘的观察证据。

[INPUTS-AFTER.json](INPUTS-AFTER.json) 回核94项消费原件无漂移；初始源在派生前记录，三份原日志在各自回放前记录，后补依赖在最终预检前对照冻结锚点记录，**没有宣称所有94项均在任务开始前采样**。r29的18项冻结清单另全匹配。实际 preflight 前/后全部原分组一致，固定14项与实际QEMU字节不变，包含同一kernel/DTB/N64CPIO/candidate；4×A35、5120MiB、MTTCG/noicount、原180秒与20秒均保持。详见 [输入分组比较](evidence/PREFLIGHT-INPUTS-COMPARISON.json)。

运行准备说明见 [RUN-TEMPLATE.md](RUN-TEMPLATE.md)。所有临时mock导出仅在本目录临时子目录，测试结束已删除；未创建长驻进程、端口或浏览器，无待清理服务。候选供下一次明确授权运行收集证据，当前不部署、不增加VM/Start次数，亦不宣称改善了真实启动成功率。
