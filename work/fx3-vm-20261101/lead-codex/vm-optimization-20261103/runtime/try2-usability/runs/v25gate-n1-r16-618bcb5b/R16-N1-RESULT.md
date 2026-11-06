# r16 N1 单轮零按键：实际结果

2026-11-04。**本轮限定范围通过：真实网页 Start、首份有效 OSD/待机图、v5 非事务尾段快照、健康门和恢复退出均有实际证据。** 总 guest 阶段 54.619892s，0 guest 键、0手动看图确认；实际只启动一轮，没有重试、没有 N64 或菜单交互，没有部署或修改冻结源/guest/平台/入口。此结果不证明 N1 带来性能改善或长期稳定性。

## 身份与冻结输入

run：`v25gate-n1-r16-618bcb5b`；专用真实 Chrome session `fx3r16-n1-52778`，1280×1200；实际 URL `http://127.0.0.1:52778/`。runner PID **79877** / QEMU PID **80065**；guest helper PID **237** / root **0x7ef1128d60**。

host launch UUID：**`e8c4eb5a-8f8a-4038-b8ae-9b9ea77a33f9`**；回显 tag **`0x9effc67005cf5b27`**。网页 Start request UUID 为独立身份 **`a1888a3b-fd59-4526-b1c0-c666d02b3463`**，不与 host launch UUID 混用。最终完整身份见 `trial-session.json`、`R16-N1-WEB-HTTP.json` 和 `R16-N1-VERIFICATION.json`；HTTP鉴权头已脱敏。

| 冻结项 | SHA256 |
|---|---|
| r16 SOURCE-FREEZE.json | `00f13330f88c67f14710ce266088f304ee5966a389f01971901b7f685a188db7` |
| r16 SHA256SUMS | `b4a0395230b544ad804a3e1948f39100ae4fd5f93d13822d2d6ed18763b88ba2` |
| 实际 runner | `165414ca8ae04382d851d7fd3d33af38d79cb35ecdce51a20d53e879b3eab45d` |
| N1 candidate | `ce047a951a5e7af08d19312d4e9d6440080e159c857e41edf90ce66607a31563` |
| N1 guest.cpio | `77081424fa73f9737434b7d0c5d2f6dc2b21215ffcc9cb3a95281dac9d4b521c` |
| 原 DTB | `5aa2beacb0b0e1f5b83f4589f9bba8b148cd73f87b6058e0f648e05c5347855b` |
| 原 kernel | `da4a66fa29f6b4033233c0d8e7bd9a6f0ffab0cc18d85a44aa6f3830b7c4820c` |
| 实际 QEMU | `bf4d46481998b8fb0644da3e17a333d5fc8a7b6aeb0035f1b4e03aa25c98c70d` |

启动前 32 frozen source / 39 delivery SHA通过，双锁 free，无既有 runner/QEMU，卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B` 正确。结束后独立重算 14 固定 input 与 32 source SHA 均相同。`command.json` 实际保留 4 核、cortex-a35、5120MiB、MTTCG、无 icount、原 DTB/kernel/Backup 等配置。正常 STATE/preflight 写入按授权发生，冻结范围未改。

唯一启动参数：`--port 0 --max-minutes 3 --max-steps 32 --snapshot-tail --gate-publish-interval 1`，没有其他诊断开关。未重复17项宿主离线测试。

## 时间与首帧

| 事件 | 本轮证据 |
|---|---|
| 真网页 Start | POST `/api/start` 20:27:07.958Z，HTTP202，一次 |
| 初始 QMP cont | id4，Popen单调时钟起点后 +0.782576s |
| 首份宿主导出的有效帧 | seq2 / epoch1 / op0x1005 / 640×480；host_monotonic 407753.790483875 |
| 首份带帧的浏览器 status | 20:27:48.464Z，Start后40.506s，HTTP200 |
| ready保存图 | seq35，host_monotonic 407758.683239250 |
| 亲看截图 | `R16-N1-first-observed.png`，保存完成mtime 20:27:55.212977Z，可见HD、AF-C、AWB等待机图标；页面显示0/32键 |
| 真网页 End | POST `/api/stop` 20:27:59.910Z，HTTP202；Start后**51.952s**，远早于180s上限 |
| 原 End stop | QMP id158，Popen相对+52.031810s；先原读回，再独立尾段 |
| 网页 final ACK | POST `/api/final-ack` 20:28:02.758Z，HTTP200；自然PAGE自动回执 |

HTTP UTC为浏览器记录的请求时间并附实际状态码；不将其冒充精确 guest 指令执行时间。receipt.created_utc 20:26:34.284456Z 在等待浏览器之前，**不能当作 guest 启动起点**。同域单调时间由tail start/query-status id176/cont id177发送与回执可夹出Popen起点 `[407713.468872208,407713.469065041]`，首份已导出帧相对起点在 **40.321419..40.321612s**。这是宿主首次导出，不等于最早原生提交或屏幕首次可见的精确时刻；无跨clock域相减，详见 `R16-N1-TIMELINE.json`。

亲看后立即 End，没有 MENU、方向键、C4、OK 或手动确认。HTTP仅4次POST：browser-ready 200、start 202、stop 202、final-ack 200；guest `/api/key` 和 `/api/confirm` 均0。native `FX3_KEY_INPUT_RECV` / `FX3_KEY_STEP_DONE` 均0。

待机原始614400B SHA `b10896e7772ab4eb12f434e8c8035ab19d41ffc4451acbe9c0ef9e0052e03051`，PNG SHA `e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4`，与已提交软件ring身份一致。网页亲看截图 SHA `b4e789363a57831c8e293bd01399b0bea26015c6d8dc59eaecf06c3e505f2dab`。这是软件OSD，未验证真实CP多层合成或实时取景。

## 原始读回和 v5 尾段

原End暂停后 16MiB `osd-ring-final.bin` 完整读回/解析通过，SHA **`67f70985891bbe1e1f5fb01b7c1eaec42582ef81a5665a97c48c74b6cbb9a741`**；943 accepted events、busy drop0、坏槽0，尾部保留256事件。最后页面/原frame seq118。独立64KiB UI bank SHA **`46230b5d4e9b85bf01a9da9f3bbbce879e2d8f031dfc8912379a4cbab13d8a62`**。原读回属于尾段cont之前，不能拿尾段结果覆盖原End观察。

尾段 verdict：**`valid_nontransactional_tail_checkpoint`**，errors为空。pre-tail query-status id176证实 paused；cont id177同id成功ACK，随后query-status id178为running、stop id179成功、id180再次paused；返回时暂停已证实。尾段单调时间：start407765.812435750、cont回执407765.814582375、串口ACK见到407765.844941833、暂停证实407765.845549958、end407765.847560250。采集32.506ms（原2s预算），含停机/两读总35.125ms；不计启动性能窗口。

nonce **`0xf78b06d3df30c218`**，PID237/root0x7ef1128d60/tag与host launch匹配；probe5、TID367。两个paused读回文件各**976B**（192B ACK header + **784B/98Q** payload），逐字节相等，SHA均 **`19f8d9c9e6481afd6e420e60aa5597fd7f90a5070cc9ae4d361f19d724e3ba9a`**。独立解析header magic/version5/长度/commit/identity、全部98Q、request重建SHA和FNV32，均通过；FNV32 stored=computed=**`0x2bd87889`**。完整98Q及字段名在 `R16-N1-SNAPSHOT-INDEPENDENT.json`，未截断成96Q。

guest clock1 copy `[50416777008,50416906000]ns`，时长128992ns；统计中的first/last使用clock7，不与clock1或host单调时间相减。原生自检串口 `FX3_UI_GATE_SELFTEST_PASS` 声明GPR31/SIMD32/NZCV/FPCR/FPSR/SP与NOP/CBNZ/BL通过；BOUND记录 `publication_interval=1 ordinary_ram_authority=1 snapshot_protocol_v5=ready`。原End UI active bank0（+0x100）发布序号8332、mirror_skip1；这是累计发布数，不是Hz或成本证明。尾段98Q的 id5..11=`[1171,1049,121,119,1147,1144,1171]`，gate_hist=`[0,0,121,432,259,359]`，last_a18=3，selftest=1、bound=1、object_mismatch=0、root_change=0。id8为119，不能称零绘制机会。

**已知回执矛盾保留：`qmp_cont_sent=false` 是初始化遗留字段。** 它与 attempted=true、acknowledged=true、id177 cont成功回复及running→stop→paused的原始QMP证据冲突，不能解释为未恢复运行。协调端消息 `msg_902e9c49efb8` 同样指出该问题；本轮没有改冻结源、修回执或重跑。

**snapshot_is_end_state=false。** 这是额外诊断cont期间自然probe形成的非事务逐原子字段检查点，ACK后到停机仍可有自然事件；之后计数未知。两读相等证明槽位不可变，不证明所有字段事务一致，也不证明它就是原End瞬间状态。N1一次成功不证明镜像成本导致或修复历史卡顿。

## 健康与收尾

health/protocol/render/diagnostic/lifecycle 均 **passed**，host_observer_error=null，early_stop_reason=null；本轮未触发ready后的原生省电关机或model power off。菜单交互未测，原 `menu_verified=false` 保留，不以健康通过代替菜单验收。

API16原20s合同通过，耗时**1.571130s**：`restore103-006-api16.bin` 精确为 `000b00b4fd7bbba9fd030091f35301a9`（SHA `1f0175375cf56ba7d5296358bd15bd91ab55fb921540c2f3197d0b12c4669c75`）；独立header解码F100FILE、shutdown_control=0x100c1ea9、restore_status=0、restore_seen=1，header SHA `e8668d6dda28642898c97841bc9ae5d653e42b7924dc2a7675e5c6d6bb2e1cd6`。host没有写原guest代码；native_unbind_return=0。

QMP quit id209有同id成功ACK及SHUTDOWN(host-qmp-quit)事件；QEMU exit0 / reaped / PID absent。独立ps确认79877/80065均消失，两个既有锁exclusive非阻塞探测均free。网页final ACK acknowledged=true，专用浏览器已close，session info active=false/pid=null。

限定kernel USB/APFS查询：pre-run本地12:11:21–12:26:21，run窗口12:27:02–12:28:07，均25s timeout上限内exit0、无匹配记录；不是总体存储可靠性证明。原查询在 `R16-N1-PREFLIGHT.json` / `R16-N1-RUN-STORAGE.json`。

独立离线核验脚本首个断言误将receipt.key_steps当列表，修正为实际整数0后全部复核通过；首份失败日志保留在 `R16-N1-VERIFY.log`，成功日志为 `R16-N1-VERIFY-2.log`。这是报告核验修正，未重启VM或更改运行结果。

交付冻结清单 `R16-N1-SHA256SUMS` 覆盖原始run和新增报告/截图/HTTP/nonce/98Q/清理证据，校验回执为 `R16-N1-HASH-CHECK.txt`。N1本轮至此封存；协调端后续另行授权的N64必须使用独立新run与报告，不并入本轮结论。交互、长稳与性能因果仍未验证。
