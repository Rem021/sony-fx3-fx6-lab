# 单帧 PNG 缓存独立候选

仅宿主离线通过，未接入默认入口，未启动 QEMU，不能据此宣称菜单提速或运行集成完成。

## 文件与复现

- `trial_ring_cached.py`：原 `../trial_ring_usability.py` 的独立候选，保留类名供后续显式集成。
- `baseline.py`：原文件逐字节快照；`candidate.diff` 为完整差异。
- `verify.py`：真实 ring 固定片段 + fake QMP 的生产 `poll` 差分验证，无替换 `read`、`save` 或文件输出实现。调用计数仅用委托包装器。
- [完整回执](verification-7ok6ftnb/receipt.json)、[静态核对](static-receipt.json)。测试输出和固定片段全部在 `verification-7ok6ftnb/`。
- 复现：`python3 verify.py`，每次创建新目录，不覆盖前次回执；禁止字节码写入依赖目录。

## 合同

每个新 seq 仍先调用原 `validate_slot`；其 FNV 路径完全不变（非法 target 原本在 FNV 前拒绝，仍然如此）。仅完整 immutable raw bytes 相等、且 `(fmt,w,h,stride)` 相等才命中；不用 SHA/FNV 判断缓存相等。每次命中仍重新计算记录中的 SHA，生成当帧 metadata，原子替换三个文件，更新 records/seen/last，调用 publish/save。缓存不持有 metadata 或 RGBA，仅保留上一项 `(layout,raw,PNG,nonuniform,all_zero)`；miss 即失效并替换，不能跨布局回用历史项。真实片段常驻 payload 为 649151 字节，上界受原验证 0x12c000 raw 和 640×480 PNG 限制，项数始终为 1。

## 验证结果

真实最终 ring 的 4267–4274 八个完整槽原样固定；global header 只改成各槽对应的 seq/epoch，以回放已提交槽。8 次均执行 validate/FNV，rgba/png 从 8 次减至 1 次，命中 7 次。所有 PNG 与基线逐字节一致，最终 PNG 也与原运行 `trial-final.png` 一致；metadata 除运行时间外一致，每个 seq 均 publish。

15 个派生输入验证 metadata 的 epoch/token/native_identity/registered_target 更新、像素变化、格式/宽/高/stride 变化、A→B→A 单项淘汰、非法 target 和 torn FNV 拒绝；13 次 publish、11 miss、2 hit，15 validate、14 FNV。拒绝样本不更新输出或 metadata。相同 seq 不重复发布；重复 evidence 标签拒绝覆盖；测试前后原输入哈希一致。原 validate_slot/evidence 的 AST 一致。

三次完整八帧 poll（含 fake QMP 文件写入、原子输出与 save）中位数：基线 548.77 ms，候选 407.79 ms，减少约 25.7%。这是 7/8 重复的固定离线片段，不包含真实 QMP 传输、客体调度或菜单响应。源运行 662 帧/681 polls、396 相邻 SHA 相同、9 种 raw SHA 的统计独立核对见静态回执；该统计不代替完整字节比较，也不外推整体收益。

## 固定哈希

- 原基线 SHA256：`4dea2f0154844e24675726727fee5bdb7bbb50456dfd15288dfdb8d7daef1bdc`
- 原最终 ring：`f385c1214f9a21cce18f59b3b52da818738ece768b4616ec1afb5e17f616d6c2`
- 八槽拼接片段：`af8b3270756b34562fef72dfc8ebebd6ae80b7e782a7a3fde830a77010d136d6`
- 候选源码：`9309794feded60291d6748bd4d19ab98a909e7ba73c91233a2ffb983551f9e11`

只读查阅 Python 官方 bytes/比较文档（2026-11-03）：https://docs.python.org/3/library/stdtypes.html#comparisons；实际测试解释器 Python 3.14.6。完整 bytes 的相等比较是缓存判定，哈希只作证据。

后续：协调端独立复核后安排运行集成。原 trial、v21、CPIO、DTB、默认入口及原运行证据均未修改。本目录不是 Git 仓库，未创建提交；入口索引限定于本 README，遵守仅本目录写入范围。
