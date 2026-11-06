# FX3 r20：单次按键 attempt 结果，离线候选

结论：保留 r19 的帧 SHA/代次预检和原服务端拒绝顺序，新增可只读查询的**本次**按键 attempt 结果及恢复资格快照。资格判断不调用 `cancel`、不重新 arm、不点击或补发固件键；没有 VM、部署或真实操作员恢复验收。只接受“本次明确未 POST”或“带匹配 request_id 的完整 4xx 未入队”作为未送达证据，accepted、在途和未知结果均拒绝。

## 代码与协议

- 仅派生 r19 PAGE/TrialState；差分 `r19-to-r20.diff`。服务端 `submit` 原六个拒绝分支、顺序、中文错误、frame SHA/gen/ABA 门、单次 `pending.append` 保持；旧请求不带 ID 时响应完全兼容。可选严格 UUID4 `request_id` 只在回应与有界拒绝记录中回显 `accepted=false,enqueued=false`，202 回显 ID 并仍只代表**入队**，不代表 guest 写入、处理或绘制完成。request_id **不是幂等键**，服务端不去重；未知 POST 严禁重试。
- PAGE 每个被 handler 接纳的显式点击在首个 await 前生成 `attempt_id`，固定 document `performance.timeOrigin`、run launch ID、key、base/expected step、点击时 seq/SHA/gen、已安装 alarm 的 nonce/固定 due。状态依次为 `preflight`、`not_posted`、`post_in_flight`、`explicit_rejected_unqueued`、`accepted` 或 `delivery_unknown`，另有 `mutation_called`；只允许同 ID 的异步完成更新当前 attempt。`fx3KeyAttemptOutcome()` 返回深拷贝。旧提示独立存在，不能作 attempt 证据。
- 预检 GET 失败、原 8 秒超时或 200/null 均记 `not_posted`，释放 busy 并等普通状态轮询恢复；POST 5xx、超时、解析失败、不完整 202、错误 ID 的 4xx 记 `delivery_unknown`，继续锁定。新 PAGE 不自动重新确认画面、重发 POST 或越过服务端检查。
- `fx3KeyAttemptRecoveryEligibility(binding)` 只读本地瞬间状态，要求精确 attempt/document/launch/nonce/key/step/点击帧绑定、原 alarm 固定 20 秒 due 未过、当前原生无错误且未 End/unknown/review/在途、步数未增、最新有效已加载帧及 ready。返回 `server_atomic_permission:false` 和快照时间；它**不是服务端锁内原子许可**。未来若调用者决定取消 alarm，须在独占操作员流程重新核对；本候选没有取消动作。缺少 alarm helper、身份或有限 due 均 fail closed。

## 离线证据

- `tests/server_audit.py` → `evidence/server-audit.json`：旧调用 3 类响应逐值相同；可选 ID 的 409 明确未入队且锁内拒绝行可关联，202 仅入队。未改变 guest 或 runner。
- r19 真实 Chrome 回放复用实际 r20 PAGE/TrialState：`evidence/fx3-r19-6e630ac7/BROWSER-RESULT.json` 为 15/15，通过 A→B/ABA、原 8 秒 GET 超时、200/null、双击、End、Start 与 confirm 等边界；该回执早于最后一次只读资格异常保护小改。
- r20 专项真实 Chrome + loopback `TrialState`：`evidence/fx3-r19-fbe4c357/ATTEMPT-RESULT.json` 为 11/11。旧 A 拒绝提示留存而 B 的 POST 在途及 accepted 均不可借用 A；本地未 POST、匹配 409 可判未入队；错 nonce/document/attempt ID、已过期/缺失/非有限 due、5xx、错误 request_id、无效 JSON、原 8 秒 POST 超时均拒绝恢复。另有已实际入队一次但 202 延迟超过 8 秒的场景：客户端保持 unknown，迟到响应后无第二次 POST，按钮点击也不会补发。报警器是**一次固定 due 的只读 mock**，不是原 20 秒 helper 的运行证明；fixture 的 guest 入队计数不是 guest 处理回执。最终源码包含 alarm status getter 异常转显式拒绝，最终 11 项测试在该源码上执行。
- 测试 session 均独立并已关闭；无 QEMU。源与输入 SHA 在 `SOURCE-FREEZE.json`、`INPUT-HASHES.json`，交付在 `DELIVERY-MANIFEST.json` 与 `SHA256SUMS`。

尚未通过：真实 VM 与操作员取消 alarm、真实恢复后新键、长时间使用。后续最小验证须先独立审查调用者身份/原 helper 固定 due，再在获授权单轮里记录 attempt ID、服务端结构化拒绝与 native down/up/done；accepted 仍完整保留原 20 秒看图合同。不要用本地资格 `eligible=true` 直接宣称可恢复或自动发键。
