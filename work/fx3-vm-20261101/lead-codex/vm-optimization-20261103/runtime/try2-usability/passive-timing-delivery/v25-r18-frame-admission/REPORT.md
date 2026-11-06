# FX3 r18 画面准入与拒绝回执：离线候选

结论：已从冻结 r17 宿主包派生独立 r18 候选。页面采用已审的视觉加载锁：新图加载期间禁键，加载完成仍须最新 SHA 与 `content_generation` 一致；同内容序号推进可以按原服务器身份规则接受，A→B→A 不因 SHA 回到 A 而越过代次。`TrialState.submit` 的原接受、拒绝分支顺序与中文响应不变；同锁内新增定长拒绝事实记录。**未运行 VM，未部署或更换默认入口。**

## 输入与变更

- 目标卷 UUID：`F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`，写入前已核。r17 `SOURCE-FREEZE.json` SHA256 `267ac6e3080511aecb4a7e8ae549d6d2f7140f6bb43eaeada9e204aa497473c0`；已核其中全部文件再派生。r17 runner SHA256 `845a1f2d33a00d10ede293d5e397c88f7b0e387460ce1f890475b5b18a4006f8`。
- 已审 PAGE 候选输入 SHA256 `ee135617204a9c724a9e9b8cb5198b2785252de66b07b662105f03b1d130b26c`；r18 内联 PAGE 脚本 SHA256 `d224a8f10786dc815520a8c11320f8625c1e969f9508bac39541c971ecfb9822`，保留 Start 修复。原 `confirmButton.onclick` 源体 SHA256 `f5f09eabc5b29fcbb12cea316f1c242b5945d310de8e431bbc6c011a82f107b7`，新旧逐字节相同，见 `operator-helpers/PAGE-IDENTITY-AUDIT.json`。
- r17 与 r18 共用的 23 个顶层 Python 文件中，21 个逐字节不变；只有 PAGE 与 runner 改动，并新增 `web_rejection_receipt.py`。完整源码变化在 `r17-to-r18.diff`。未复制 guest、CPIO、DTB 或整项目；固定 FX3 平台、N1/N64 槽包、5000ms 原厂门、20s 恢复与输入/退出政策均未更动。
- 拒绝队列容量 64，记录总数与截断数；每条仅含单调时钟、固定原因/失败谓词、已观察及当前 seq/SHA/gen、render/phase/busy/review 等有限状态，不含 token 或任意请求体。锁内无磁盘 I/O。结束时深拷贝导出 `web-key-rejections.json`，零拒绝也导出零记录；写文件失败有独立不完整回执，不能变成健康通过。`web_rejection_receipt.py` 由 runner 在原 QEMU 清理块之后调用；本轮仅静态 AST/假状态核验该接线顺序，**不是新增 VM 退出验收**。
- 三项操作员辅助只将 PAGE 指纹钉到新 canonical 脚本；旧 PAGE、错 PAGE 拒绝，CLI 与 `capture_after.js` 不变。原 8s 捕图/余量、20s nonce、明确单次确认及旧帧/历史 ACK 与当前 ready 分离的合同不变。脚本确认仅用于离线受控 fixture，不是人眼语义判断。

## 离线验证

| 验证 | 结果 | 回执 |
|---|---:|---|
| 实际 r18 `TrialState` 拒绝对比/有界队列/深拷贝/零记录导出/结束接线 | 13/13 | `evidence/rejection-delivery-test.json` |
| 实际 r18 PAGE + TrialState Chrome 受控回放：无首帧 Start、加载窗口、同 SHA 序号、A→B/ABA、409 后新图手动键、503 送达未知 | 11/11 | `evidence/run-1793830854968/RESULT.json` 与同目录 PNG |
| 实际 r18 PAGE Chrome 辅助集成：旧指纹拒绝、新指纹安装、历史菜单 PNG 捕取、显式确认后取消原 alarm、错 PAGE 拒绝 | 8/8 | `evidence/helper-run-538ce8a4/RESULT.json` 与同目录 PNG |
| Python 编译 | 通过 | `python3 -m py_compile`，无 VM |

上述浏览器为本地 loopback fixture，未向 guest 输入键。服务端原帧身份准入没有放宽；409 竞争保护仍可能在实际人眼观看和 POST 之间触发，r18 的新增记录可区分当时 observed/current 状态。页面已加载且 ready 才可再次由人主动点击，任何拒绝或未知送达都不自动重发。测试不是固件绘图、菜单、保存、生命周期或外盘运行通过证据。

## 待审真实轮

仅在协调端另行授权、卷/进程/双锁/固定包哈希复核后，沿用既有单实例 QEMU 与浏览器 Start，建议候选命令（**本次未执行**）：

```sh
python3 /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/v25-r18-frame-admission/run_trial_v25_diag_r3.py --snapshot-tail --gate-publish-interval 64 --max-minutes 30 --max-steps 4096 --port 0
```

逐键查看真实 PNG 再决定并显式确认；记录被拒绝键的 `web-key-rejections.json`、浏览器提示、native down/up/done、API16 原字/ACK、QEMU reap、双锁释放。不能用本离线结果代替任何一个运行门。N1 仅在后续独立批准时换 `--gate-publish-interval 1` 对照。
