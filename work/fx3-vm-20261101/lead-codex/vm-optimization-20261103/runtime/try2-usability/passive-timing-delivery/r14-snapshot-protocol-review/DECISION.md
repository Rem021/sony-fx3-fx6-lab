# r14 nonce快照协议：值得实施，但不是End末态或严格吞吐计量

2026-11-04。**有条件建议实施：普通RAM保留唯一权威st；下一自然probe把它复制到既有观察区的独立快照，提交后不再改写。** 不需要PFN、mlock或在uc映射上做原子RMW。仅一个checkpoint能保留有界采集区间的累计计数；**不能还原更早End暂停瞬间的精确计数，也不足以单独证明mirror成本因果**。

只读原v11、r13归档host收尾/控制mailbox源码。未实现、编译、VM、下载、扩扫或改旧文件；卷UUID写前已核对。给ctx_f33282e02d7f的同步意见通过协调端转发。

## 最小区域与guest协议

v11 `fx3-ui-gate-v11.c:6–12,63–70,78–89,103`：st在普通RAM，原子访问留在那里；两bank实际payload为+0x100..0x400与+0x1100..0x1400，boot记录从+0x4000开始，上部另有+0x7800、+0x8000、+0xb000、+0xc000、+0xc800、+0xd000用途。以下只占当前v11空闲的+0x3000..0x3400，不碰旧header/bank/boot；**候选原PFN描述必须由新version替换，不可与之叠加**，实现者须再核候选新增字段。

| 物理地址相对0x41dc00000 | 唯一writer | 用途 |
|---|---|---|
| +0x3000..0x3040 | host，guest停止时写 | request：新magic/version、run身份、pid、64位nonce、slot/长度、最后写的32位commit |
| +0x3040..0x3100 | 单个guest采集writer | ACK元数据：对应身份/nonce、probe id/tid、clock id1起止ns、nontransactional标记、校验和、最后写的32位ACK commit |
| +0x3100..0x3400 | 同一guest采集writer | 原96Q statistics的768B快照；成功后整个run不可复用/覆盖 |

host初始化描述符后最后提交request，读回核对；guest只用对齐volatile 32位普通load/store访问该映射及显式dmb，不把nonce/锁改成uc上的LDXR/STXR等原子操作。64位字段按两32位搬运，单写者、提交位最后发布；在已证guest停止状态下写request避免半描述符并发。普通RAM的独立trylock/完成nonce用于多proxy争抢：失败立即返回原流程，请求保持pending；拿锁后重新核nonce与完成态，只允许一个writer，**不借用mirror_lock、不spin、不暂停其他probe更新st**。

接线放在既有probe本次计数/字段更新后（普通id和boot_event两条return路径均覆盖）；按原原子load逐字段取st，保存两次独立CLOCK_MONOTONIC id1时间，再写快照/元数据，dmb，最后ACK commit，再dmb。保证原返回、errno、寄存器及Sony原指令/计数/消息不变；不调用原timer/draw，不新增线程。**96字段不是同时刻事务值**：其他proxy可在复制区间继续改st，时间必须标为[copy_begin,copy_end]，不可只给一个“精确采集时刻”。commit后设置本run已完成状态，后续probe只快速退出此协议，绝不重写已提交slot。

## host接线与明确时序差异

r13 `run_trial_v25_diag_r3.py:690–704` 的InputGate写原本在QMP stop/cont之间；`gate_input_usability.py:34–50`仅提供物理GDB M及读回，**没有运行态写不隐含暂停的证明**。因此不继续研究运行态GDB，也不宣称零新增stop/cont。协调端已确认可接受显式有界采集尾段，建议：

1. 原End stop仍由 `capture_quiesced_diag()` 执行，先保留原16MiB ring与原paused optional读回（runner:754–807，包括后续frame/native-file读回）。**性能/首帧/交互观察窗在这次End stop结束**；这些原读回不得被后续尾段的新帧覆盖。采集尾段接在这些读回之后、`restore_native_api()`（:811–812）之前，再核paused；prelaunch、身份缺失或transport send_unknown时不为取诊断而恢复guest。
2. 仍停止时，通过新增独立`diagnostic_snapshot_request()`写上述nonce并读回；不借`InputGate.command()`伪造按键或增加key step，也不借`shutdown_control()`提前触发恢复。所有GDB/QMP/socket操作都受同一诊断绝对预算约束，不能沿用3秒阻塞后仍宣称预算内。
3. 预算仍有效才新增一次cont，让**自然下一probe**服务请求；guest仅为本nonce输出一次完整串口ACK，host用已有log monitor有界等待。ACK通知不用运行态GDB轮询，避免其暂停语义未知；这一行额外诊断I/O及等待也属于尾段。建议候选总预算2秒，具体预算由实现配置固定，不侵占/放宽原API16恢复20秒合同。若写请求阶段已超时，保持停止并直接原清理，不再cont。
4. 收到匹配串口ACK或到期后，**新增一次stop并query-status证明paused**，读独立slot，核magic/version/run/pid/nonce/长度/commit/校验和。两次相同读取只验证已提交slot未变化，**不是证明稍后pause时st与slot相同**。随后无条件进入原restore/quit/reap路径；不再次调用会额外stop或覆盖原ring的完整capture函数。

相比原收尾，新增诊断request写、一次cont/stop、最多一个预算内的guest运行尾段、一次ACK打印和slot读回；没有新增周期线程，但**确实新增了Sony自然事件可继续执行的时间**。需要分别记End-stop、tail-cont、ACK-arrival、tail-stop等host monotonic时刻；guest copy起止仅在guest id1内解释，不与host或旧gate clock7混减。原optional/恢复接线应拆分清楚，禁止把尾段事件/延迟计回性能窗，也不能保证它对之后清理状态毫无影响。

## 必须失败关闭的边界

| 情况 | 结果/动作 |
|---|---|
| 多proxy、trylock忙 | 保留pending，原probe不等待；另一自然probe可完成；不触发原业务重试 |
| 无后续probe、超时、断连或ACK错nonce | 诊断unknown，预算到期即stop并继续原恢复/退出；不强制原函数、不重发业务消息；transport send_unknown沿原错误策略，不盲发cont |
| stop打断复制、ACK commit未写 | 原始slot可封存，不能解析为有效统计；之后restore的cont即便完成它，也只能算late/cleanup数据 |
| 串口ACK已见但slot版本/nonce/校验不符 | unknown，不能用旧bank/PFN结果降级为“精确末态” |
| ACK至pause之间又有事件 | `snapshot_is_end_state=false`、`post_snapshot_event_counts=unknown`；快照保持不变，不能用双读相同推断期间零事件 |
| OSD ring全零或解析失败 | 独立快照仍可核验；各自报结果，互不冒充有效；诊断失败不跳过原清理尝试 |

## 本轮能比较什么

**能比较**：N1/N64相同固定平台/原指令与统计语义下，原End之前的首帧、画面和已带同钟时间的既有输入证据；slot提供到copy区间的累计命中和低水位机会。若某单调累计count7/8在更晚slot仍为0，且绑定身份/无reset成立，可支持更早End之前也未命中；若为正，**不能排除全部增长发生在采集尾段**。

**不能严格比较**：原End瞬间a18、原性能窗内精确生产/消费速率或Δcount、ACK到pause之间新增事件，以及mirror的CPU耗时份额。一次checkpoint不能同时满足这些要求，不能凑成“根因已证”。本方案值得作为**可靠采样与候选筛选**实现；若本轮硬验收要求精确End末态/窗口吞吐，应直接判不足，另设有明确时间边界的至少两次checkpoint或独立耗时设计，不能继续称本次单slot达标。

最小离线反例：nonce/身份错配、多proxy同时claim、在每个payload/commit步骤暂停、N−1次后End、无probe、ACK日志丢失、ACK后有事件及全零ring；确认原消息/返回/errno和清理分支不因诊断失败改变。当前只给设计，未运行这些测试。

输入来源与哈希见 [INPUTS.json](INPUTS.json)，本次交付哈希见 [SHA256SUMS](SHA256SUMS)。
