# AP95 宿主逐步输入计划（准备回执）

2026-11-02。**单步输入实现与宿主验证完成，删除键未启用，AP95尚未运行。** 基线是已封存的 AP94-r4，首次设置/拍摄待机/MENU浏览仍待guest验证。合同 Lead msg_8162589b2b22。

## 新控制协议

沿用独立软件预留区 `41df00000/64KiB`，只改本次新软件协议；不写原UI状态/参数/缓存/回调。新magic `3545594b334d5253`，host仅写+8处12B：`u32 step/key/hold_ms`。guest回执：+24 done、+28 donekey、+32/+40 down/up ns、+48 donehold、+52 result、+56累计原生send数。旧AP94的8B协议不兼容，magic不符会在host写入前停止。

取消固定按键序列和自动首次UP。guest没有新step就不发键；每个有效step只发一个原生20B down和一个up，原队列807a0020/源00410025/from_type1，原接收者原生free所有权不变。step严格单调、最多30；已审计六键白名单UP3/DOWN30/LEFT15/RIGHT1af/ENTER1ac/MENU1ab，hold限制50..200ms，默认选择100ms，避免构造长按试验。未知键/顺序错误/原队列或缓存失败立即停；删除键审计获准前参数为0且被拒绝。

宿主每步必须填写实际画面描述和理由、显式hold，且上一指令已由guest完成；本地Unix GDB仅写新软件控制字并读回核验。driver在每次up后导出独立物理QMP PNG并要求SHA与原native lease committed snapshot相等；由运行持有者实际查看后再选择下一键，间隔≥4s。phaseA初始图也须先查看，无自动UP。新源码独立版本保存，未修改AP94 helper/历史run。

## 验证

- [准备回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap95-hoststep-preparation.json)：核心 C ASan/UBSan验证六键、30步/第31步拒绝、乱序/未知/待审计删除拒绝、时长边界、准确20B down/up。
- [宿主mock回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap95-hoststep-host-test.json)：本地GDB模拟器30步、必须先guest done、错误在零写时拒绝，每步唯一12B地址，构造/等待时不发指令。没有真实QEMU/guest写入。
- [实际guest输入线程宿主运行日志](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/check-hoststep95-worker.log)：在ASan/UBSan宿主替代 `/dev/mem`/原OSAL边界，执行新keyworker本身；等待多次无指令不发键、同step不重放、两条明确命令恰4次原20B send、50/100ms hold、源字段精确、原接收者free恰一次；第三条未知键在发送前拒绝，线程停止。不是guest/Linux/硬件验证。
- [六键guest ELF构建](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-rm-empty-provider-v5-hoststep-build.json)：交叉编译/链接0；删除宏默认0，尚未纳入候选运行。

[只读删除键静态补充](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap94-delete-key-static-supplement.json)仅说明原app名称表/配对表TACT_DELETE UI23→Infra1f8；未证明本机设置页回调/完整原配置，不能据此启用。Lead已另派 `audits/key-delete-c4` 独立审计；得到固定proof与授权后才生成允许删除键的新版本、构建候选并运行AP95。
