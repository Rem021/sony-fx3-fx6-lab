# v22 导航确认候选（尚未部署）

本目录只包含从 v21 派生的宿主 runner/web 和已审定缓存 reader；沿用 v21 固定 FX3 guest 候选。先看 [REPORT.md](REPORT.md)、[SOURCE-FREEZE.json](SOURCE-FREEZE.json) 与 [VERIFICATION.json](VERIFICATION.json)。本轮只跑离线及真实浏览器历史画面 fixture，没有启动 QEMU。

下一次获唯一运行窗口后，协调端可审核并运行：

```sh
python3 -B /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-usability/passive-timing-delivery/navigation-review-v22/run_trial_v22_navigation_review.py --port 8765 --max-minutes 15 --max-steps 32
```

runner 默认仍是 60 分钟、4096 键；上例仅为下一轮有界验收参数。网页会在每个原生输入完成有限观察后要求人实际看清当前画面并点击“我已看清当前完整画面，继续”。该点击不发送固件键。真实 guest 验收与 31/32 键边界仍未完成，故此处不是面向用户的正式启动入口。

回退：沿用原 v21 runner/入口，勿覆盖本目录或旧候选。浏览器 fixture 仅使用历史 PNG，可读回执位于 `browser-v22-final-*` 和 `browser-v22-receipt-*`；其中 `browser-v22-chronological-*` 是先前试验记录，不作为最终源码冻结依据。
