# FX3 首键新鲜度 r19：离线候选

结论：服务端 409 是正确的旧画面竞争保护。r18 PAGE 仅以最近一次已知轮询状态判断，点击到 POST 之间若服务端更新，仍可能被拒绝；r19 在一次点击中先锁住本次操作、只读 GET 一次当前状态，再按原 SHA、代次与生命周期门决定是否执行原单次 POST。它只能缩小已知窗口，GET 后到 POST 前仍可更新并由原服务端 409 拒绝；不保证消除所有 409，也不解决约 95.8 秒操作延迟。未运行 VM、未部署。

## 实际输入与像素

真实 run `v25gate-n64-r17-65cecb63` 的 `web-key-rejections.json` 记录一条原子拒绝：observed seq116/gen24/SHA `2914275c…`，current seq124/gen25/SHA `e0140ea1…`，失败谓词 `sha_mismatch` 与 `generation_mismatch`；当时 ready/render_valid 均为 true、steps=0。导出在清理后，不能充作拒绝瞬间的第二张 PNG。该 run 持久保存的 `trial-frame.png` 为 observed 原字节；current `e014…` **未在该 run 保存**，像素对比使用 `coordinator-pixel-difference-review/e014…png` 的历史同 SHA 原字节，来源与完整哈希见 `evidence/pixel-difference.json`。两张 640×480 RGBA 图有 885 像素不同（0.2881%），差异框为 `[364,7,448,27)`，全部在最上方 120 行；不推断闪动区域的 UI 语义。

## 变更与边界

仅派生 r18 的 `trial_web_v22_navigation_review.py`，差分见 `r18-to-r19.diff`。按钮回调在第一次 await 前固定点击时 step、SHA、content_generation 并将 `busy=true`；仅一次只读 `/api/status` 完成后，要求该状态、当前已加载图、最新已知状态仍与点击时 SHA/代次/step 一致，且 phase/ready/busy/review/未知送达/End 均符合原准入。seq 可以在同内容同代次时前进。若不一致，0 次 POST、显示“本次未发送”并等待原 tick 只读刷新；新图加载后绝不自动转发旧点击。GET 异常或原 8 秒超时没有 mutation，冻结键直到正常 tick 恢复；迟到 GET 不发键。POST 仍仅一次，后端原 SHA/gen/ABA 校验、409 与 5xx 送达未知政策不变。Start、confirm handler 与服务端代码未改，所有 helper PAGE pin 未改。网页加载锁、缓存、恢复退出与 guest 皆未动。

## 离线实测

真实 Chrome 单独 session + 实际候选 PAGE/TrialState + 受控 loopback fixture，最终 `evidence/fx3-r19-39a8726e/BROWSER-RESULT.json` 为 14/14 PASS，带每步 PNG、DOM 状态与 key/confirm 请求计数。关键场景：预检 GET 挂起时普通 tick **先**完整加载 B（displayed 与 lastStatus 均 B），再释放 GET，0 key POST；A→B→A 到 gen3 同样 0；同内容同代次 seq 前进 1 POST；预检后服务端再更新仍由原门返回 409 且 0 入队；双击最多 1 POST；5xx 未知送达锁定；GET 失败与原 8 秒超时 0 POST，超时后普通 tick 恢复按钮、迟到结果仍 0，新的明确点击才 1 POST；End 在预检中 0；原确认 1 confirm request 且无额外 key；无首帧 Start 可用。历史早期 13/14 场景回执保留，不作为最终通过依据。Fixture 的 publish/点击为受控测试，未伪称人眼验收或真实固件结果。

下一次最有区分力的单轮验证：在独立授权的真实页面，对每次显式首键记录点击时已加载 SHA/gen、预检 GET 的 seq/SHA/gen、服务器锁内拒绝记录与原生 down/up/done；若仍 409，对比是否发生在 GET 后、POST 前。仍须每键亲看真实画面、完整退出并核双锁，不自动补发。此轮没有申请或启动 VM。
