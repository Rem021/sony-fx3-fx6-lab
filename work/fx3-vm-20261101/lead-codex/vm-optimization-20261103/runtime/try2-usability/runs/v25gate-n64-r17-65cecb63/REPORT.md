# FX3 r18/N64 八步验证：failed（首个 MENU 被 409 拒绝）

本轮仅一次 VM，Start 一次、MENU 网页请求一次，**实际 guest 输入 0、人工确认 0、合格菜单截图 0**。首帧与运行健康通过，但八步导航失败；第 2–8 步未执行，不补键、不重开。

## 身份与冻结

新 run `v25gate-n64-r17-65cecb63` 沿用 r17 标签，实际运行 r18 源码 SHA `c429f375d57a288370fefda0aedb62270fce96220d5b885d12f5ff27f69e789b`。host launch UUID `f93c6762-21ea-41d7-8880-2b33ab2c1801`，网页 launch ID `814fbfaf-1a13-43c2-91d9-876a526a19a8`。

卷 UUID 正确；35 个冻结源、67 行交付清单（DELIVERY-FREEZE 66 项）、14 个固定输入全部前后匹配，旧 R18-RESULT SHA 匹配。`OPERATOR.py`、验证模块、两个 review 脚本和 END409 原样复制并在 Start 前冻结；URL/session/每步新 nonce 提前准备，原 PAGE 在真实 Start handler 内生成 launch ID，所以实际 ID 在点击后写入配置，首次 arm 前完成。helper 只用 r18/operator-helpers。源码、旧 run、r10 入口与 ledger 未作人工修改；原 runner 按既有行为更新其运行 checkpoint。

唯一命令：

```text
python3 -B passive-timing-delivery/v25-r18-frame-admission/run_trial_v25_diag_r3.py --port 0 --max-minutes 8 --max-steps 32 --snapshot-tail --gate-publish-interval 64 --pre-input-snapshot-step 2
```

固定 FX3 kernel/DTB/cortex-a35/4 核/5120MiB/MTTCG/noicount/N64 CPIO 不变。启动前无其他 runner/QEMU，双锁空闲。独占单标签 `fx3-deadline-v25gate-n64-r17-65cecb63`，1280×1200，`http://127.0.0.1:58014/`。未运行 fixture，无 FX6、物理设备、USB/SD 或刷写操作。开始前只核对 [QEMU 官方参数文档](https://www.qemu.org/docs/master/system/qemu-manpage.html)，未据此修改冻结配置。

## 实际结果与时间

时间均为 2026-11-04 UTC；不同 clock 原点不相减。首个 host 导出帧距 Popen **37.838131–37.838308 秒**，满足 180 秒门；最早浏览器显示/模型实际接图时刻 unknown。`standby-page.png` 已亲看完整待机图标，不能算菜单验证。

|事件|时间/结果|
|---|---|
|Start HTTP|22:45:32.239，202|
|原 20 秒 arm|22:46:25.918；nonce a49c1154-3fcc-4046-bbd2-192a07329a9e|
|MENU click 工具边界|22:46:25.927172–25.936329|
|唯一 key HTTP|记录时间 22:46:25.962，409|
|bounded helper|22:46:25.984490–25.999897，exit 2，explicit_key_rejection，未尝试截图|
|capture 返回|22:46:26.007531，operator_refused_or_unknown|
|原 End HTTP|22:46:30.362，202；key→Stop 4.400 秒|
|网页 final ACK|22:46:33.063，200|
|终态 JS 快照|22:46:40.908，finished/ending true，End disabled|

下一工具仅读出 explicitRejection、phase ready、End enabled 后立即点击原 End，没有等待刷新、重试、确认或 cancel。**409 专用 END409.py 未执行，也未保留 End 前的 409 现场截图及逐键 disabled 状态，这是本轮诊断缺口。** `final-page.png` 为 End 后终态图，亲看显示“本轮健康检查通过，资源已回收”，所有按钮灰置；画面没有可见拒绝提示，JS 中仍保留 explicitRejection，不能据此证明拒绝当时提示是否可见。原 alarm 未延期、未重 arm、未 cancel；终态快照尚为 armed，之后关闭专属浏览器，不把此快照称为 expiry/cancel 回执；只有一次 stop HTTP。

## 原始拒绝证据与 PNG 路径

`web-key-rejections.json` 原字节 **1131 B**，SHA **1b27917ad99ba002210ff418323d83b222152a1eaaecefb99d7602fb6cafca07**，与 receipt 完全一致。total/stored=1、truncated=0；本轮不是零记录，旧轮零记录文件未动。唯一拒绝在 host monotonic_ns `416071473275541` 同锁取样：

|身份|observed|current|
|---|---|---|
|seq / generation|116 / 24|124 / 25|
|PNG SHA|2914275caea536ff83d3bd1f884dfb1934e456fb782b5569240547e6add0182e|e0140ea1b701cf45e51290ee48835946edc28078954970230a56617964d56ec4|
|host frame monotonic|416070.733972583|416071.255589125|

failed predicates 精确为 `sha_mismatch` 与 `generation_mismatch`；render_valid=true、ready=true、phase=ready、steps=0、busy=false、pending_count=0。这是服务器拒绝画面身份过期的证据，不能称固件无响应，也不能由此归因旧轮 95.8 秒空窗。

observed 的现有原生 PNG 为本 run `trial-standby-ready.png`（`trial-frame.png`、`trial-final.png` 同 SHA）。**current seq124 的确切 e014… 原生 PNG 未持久保存，无法提供第二份已有文件路径**；对应身份/导出时间保存在 `osd-ring-readback.json` 和原拒绝 JSON，不能拿另一帧、旧轮整页截图或重编码图冒充。导出 host monotonic_ns `416077892290583`，边界 `after_qemu_cleanup_before_browser_final_ack`；不把导出时间当拒绝发生时间。`standby-page.png` 和 `final-page.png` 是 1280×1200 网页图，与原生 PNG 区分。

## 收尾与健康

health/protocol/render/diagnostic/lifecycle 均 true。原 API16 保留 20 秒恢复合同，1.572881 秒完成，原 16 B `000b00b4fd7bbba9fd030091f35301a9` 实读及 SHA 核验；raw F100FILE/control=0x100c1ea9/status=0/seen=1。QMP quit ID 237 同 ID ACK 与 SHUTDOWN、exit=0/reaped=true；runner 16963、QEMU 17157 独立 ps 均消失，双锁独立探测 free。网页 final ACK 200、专属浏览器已关闭，端口无监听。

原暂停诊断环 16MiB SHA 核验，1456 条事件、0 dropped、0 torn；原生 KEY_INPUT_RECV/KEY95_STEP_DONE 均 0。v5 尾段两个 976 B 槽原字节相同，独立头/48I/98Q/FNV/tag/nonce/root/PID 验证通过，QMP cont/running/stop/paused ACK 匹配；它是 `valid_nontransactional_tail_checkpoint`、`snapshot_is_end_state=false`，不冒充 End 瞬时状态。step2 前快照未触发。

入口证据为本报告、`VERIFY.json`、`HTTP-EVIDENCE.json`、原 `receipt.json`、`operator-step-01/`、`web-key-rejections.json`；`SHA256SUMS` 封存本 run 全部普通工件。**完整八步仍未通过；单步目标截图也未取得。运行健康与 cleanup 通过不替代菜单验收，未追加 VM 或 fixture。**
