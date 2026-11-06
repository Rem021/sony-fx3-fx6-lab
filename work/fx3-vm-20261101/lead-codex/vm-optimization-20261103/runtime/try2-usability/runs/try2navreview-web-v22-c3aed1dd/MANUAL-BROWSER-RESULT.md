# v22 browser + FX3 guest 单轮结果：首键前原生关机

**结果：未通过菜单及 31/32 键验收。** 实际固件按键 0；本轮没有点击 MENU/LEFT，也未点击 host 确认。guest 已显示可读待机图、网页七键可用，但在首键之前出现原生 power-off 请求，随后原生 shutdown screen；runner 按故障门停止。没有重启 VM 或发送保活键。

## 身份与时间线

- 卷 UUID `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`；启动前检查两锁 free、无其他 QEMU。v22 runner/web/cache SHA 分别为 `3ee1422bdd75ce82f4e67ebf4323810a67ccfe82dd1d3f075b2a393f1c8185ff` / `6f1a3ae9017162a5941b98df5eb87a72c9b64a806f6e11a5b185ea2af1095e1a` / `9309794feded60291d6748bd4d19ab98a909e7ba73c91233a2ffb983551f9e11`。guest CPIO/DTB 是原 v21 固定 `e0f05f36...` / `ffcc274a...`，输入原件与 SHA 见 `receipt.json`。
- `trial-session.json`：runner PID 72078、QEMU PID 72081、随机 loopback `http://127.0.0.1:60529`，`max_seconds=1800`、`max_steps=4096`。独立 Orca 标签 `d8c8a2e8-a1d3-4bd2-ba49-573a564237e8` 已关闭；未接触用户 8765 标签。
- run `created_utc=2026-11-03T18:36:05.381207Z`；`trial-phaseA.json` 为 read-only standby frame 和 native load/readback 证据。18:37:09Z 浏览器实际截图 `manual-browser-standby.png`：待机完整可读、0/4096、七键可用，尚无菜单；截图源 SHA256 `b4ba1ef593589b61c49c9a0d34fd15e15708242b6b458e8770bd011e3e2d1515`。此时原生待机已就绪。
- 在这张待机图后、任何浏览器固件按键前，协调端报告发生 Orca 容量错误；该错误的精确壁钟起点未由本 run 记录，不能从 guest 时钟倒推。随后的人工/工具间隔让 guest 持续空闲。`receipt.json` 的总 host 运行时长为 **340.857783 s**，`key_steps=0`，`visual_outcomes=[]`，没有 `trial-step-*` 文件。
- 原串口 `FX3_BOOT_QUEUE_SEND tid=379 bytes=28 source=0x830128 raw=2c000300... caller_relative=0x2eacd4c passive=1 completion_not_assumed=1` 被 runner 记为 `native_model_power_off_observed`；随后原生 `open screen: scr0132_0001 -> scr0039_shutdown`，`native_shutdown_after_ready=true`。发送 marker 本身不证明消费，但后续 shutdown screen 是不同的原生关机证据。精确 power-off 发起时刻未在 marker 中带可与 host 单调钟直接相减的时间字段，不混钟计算。
- `manual-browser-final.png` 在 18:42:41Z 显示“试用已结束，模拟器已退出，资源已回收”和 power-off 错误、0/4096；源 SHA256 `640a2c2c80e05662bfaffc27319d8ec374a98877dfdd546e19fd2193f87c78bd`。网页 `trial-web-final-receipt.json` 为 `acknowledged=true`。这是故障自动收尾与最终网页 ACK，**不是**人工 End 成功路径，也不是菜单验证。

## 资源与健康回执

`receipt.json`：`stop_cause=health_failure`、`health_pass=false`、`render_pass=true`、`protocol_pass=true`、`lifecycle_pass=true`、`standby_ready=true`、`menu_verified=false`。`qemu_exit=0`、`process_reaped=true`、两 PID 缺席；20 秒规则下 guest ACK 与原 API16 字节核对成功（`cleanup.restore103.passed=true`、`API16_restored=true`）；`inputs_unchanged=true`。退出后独立 `flock` 核两把 `.run.lock` 均 free。网页最终状态实际读取，随后只关闭本轮 Orca 标签。无新 guest 键，因此不存在 down/up/done 步骤；第 31/32 键全部未验。

## 原因范围与下一步

此轮首先触发的是**原生空闲关机**，不是已发送按键无响应或 v22 导航门失灵。浏览器在待机时已加载并可控；容量错误/工作流中断发生在开始互动前，造成约数分钟空耗，是否独自解释全部原生计时细节仍未知。不能由本次把 FX3 模型判定为普遍不可用，也不能把 host fixture 视为 guest 菜单通过。

建议在新的独立 host 候选中增加**启动前就绪握手**：先完成卷/候选静态检查并绑定本地 HTTP，实际打开独立浏览器页，验证页面脚本、状态轮询和按钮可控，由操作者显式点击“开始本轮”这一 host-only 操作后才获得运行锁并启动 QEMU；若浏览器不可用则在启动 guest 前结束。该操作不能发固件键、不能写 guest RAM、不能改变原生省电时限或注入 keepalive。guest 启动后仍等待真实待机图，再逐键看图；如果控制端失联则保持原健康/关机故障门并按预算收尾。v22 冻结源码本轮未改，此建议需单独 diff/离线验证后重新获得运行授权，不能在本次已结束的单轮上重开。
