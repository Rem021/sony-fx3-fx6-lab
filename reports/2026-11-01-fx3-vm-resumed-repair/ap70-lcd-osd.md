# AP70：LCD 亮度软件接受与 OSD 静默接受

AP70 通过 80 秒运行及收尾核验，解除 TID334 的 0x11a 等待点；原 0x111a 被消费并释放 result=0，随后发送 0x429、0x500。0x159 接受 mask7 且不发送回复。仍无菜单或硬件完成验收。

动态栈修正：本次实际为 `sequence_display_setup::set_lcd_brightness()`（函数名字符串 VA 0x3922a98），经 appFw+0x2b8b488 → +0x2dcfd94 → +0x2dea398 → send_and_wait_cmp_i(+0x2de70a8)，不是已证明执行独立的 `sequence_set_lcd_brightness::run()`。原 +0x2b8b650..+0x2b8b69c 引用 BACK_LIGHT_MODE 字符串 VA 0x39226c6 并调用 +0x2de0094；运行在 0x111a 释放之后，TID334 向 0x5503e0 发 tag1=0x300f6，再发送 0x429/0x500，证明同一亮度设置路径已越过 BACK_LIGHT_MODE 后续点。不能将特定 sequence 名称的先前静态猜测冒充动态证据。

实现 v25 从 v24 插入生成：0x11a 仅接受完整14B `0d201a010e000180010e000e0600`，保留payload、selector1/brightness6、pending_hardware=1，向来源回12B `0d201a110c00018000000000`，成功释放请求；分配失败不改状态、发送失败回滚状态并释放新回复，未知值拒绝不回复。0x159 仅接受固定10B头、padding0、mask3或7，保存4B legacy payload、pending_f030=1，释放请求且不分配/发送回复。标记均明确 physical_complete=0。

ASan/UBSan 宿主检查通过（含已有模型回归、24000次锁检查）：LCD正例、原回复字节/租约释放、发送失败回滚、分配失败、14个字段逐字节变异和长度拒绝；OSD3/7、4B状态、全部其余mask、header/padding/长度拒绝及无回复断言。交叉编译、CPIO重建和DTB initrd-end更新通过。工具选项参照 [Clang ASan](https://clang.llvm.org/docs/AddressSanitizer.html) 与 [UBSan](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)，协议依据本机原件审计。

运行 `ap70lcd-f61554d9`：qemu_exit=0、process_reaped=true、inputs_unchanged=true、missing_markers=[]、host_observer_error=null、guest_exception_markers=[]；进程PID独立确认不存在、两把锁独立重取后释放；AP/CP原件SHA与审计proof一致。80秒已覆盖guest约458秒的0x11a，无需加长；guest时间和宿主墙钟不同。历史候选/helpers/runs保留。

## 0x11a 后的服务请求时间线

时间列为串口中最近前一条内核时间戳（秒），仅近似定位，不能当精确发送时刻。完整payload、动态栈、行号和全部UIPC差集见运行摘要；这里长包只展示前24B。所有VA为appFw相对地址；运行基址为0x7f31c73000。

|guest时间≈|目标|命令|字节/头部|等待类型|调用者 VA|
|---|---|---|---|---|---|
|458.183281|0x92840747|0x429|10B `0d2029040a0001800000`|无需回复: send_no_wait_i +0x2de83b4|+0x2de8550|
|458.573781|0x92840747|0x500|10B `0d2000050a0001800100`|无需回复: +0x2de66f4, snd+0x2de6880后直接返回|+0x2de6884|
|554.481781|0x92840747|0x16a|8B `0d206a0108000180`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|
|554.481781|0x92840747|0x159|10B `0d2059010a0001800700`|无需回复: send_no_wait_i +0x2de83b4|+0x2de8550|
|554.481781|0x92840747|0x14c|40B `0d204c012800018007010100000000008002e00100000000…`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|
|554.481781|0x92840747|0x14c|40B `0d204c012800018007010100000000008002e00100000000…`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|
|554.481781|0x92840747|0x14c|40B `0d204c012800018007010100000000008002e00100000000…`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|
|554.481781|0x92840747|0x147|776B `0d2047010803018001000002000000008002e00100000000…`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|
|554.481781|0x909c015b|0x101|12B `000001010c00010001000000`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|
|554.481781|0x909a015a|0x109|12B `002509010c00010000000000`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|
|554.481781|0x92840747|0x161|10B `0d2061010a0001800000`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|
|554.481781|0x90040193|0x403d|16B `05003d40020000800080000001000000`|未审计|+0x2e2fd40|
|571.414531|0x90040193|0x403d|16B `05003d40080000800080000000000000`|未审计|+0x2e2fd40|
|571.414531|0x90040193|0x4037|16B `050037400900008012000000ffffffff`|未审计|+0x2e2fd40|
|571.642562|0x90040193|0x403d|16B `05003d400a0000800080000001000000`|未审计|+0x2e2fd40|
|571.950593|0x90040193|0x403d|16B `05003d400d0000800080000000000000`|未审计|+0x2e2fd40|
|571.950593|0x90040193|0x4037|16B `050037400e00008004000000ffffffff`|未审计|+0x2e2fd40|
|572.231093|0x90040193|0x403d|16B `05003d400f0000800080000001000000`|未审计|+0x2e2fd40|
|572.472156|0x90040193|0x403d|16B `05003d40110000800080000000000000`|未审计|+0x2e2fd40|
|572.472156|0x90040193|0x4037|16B `05003740120000800d000000ffffffff`|未审计|+0x2e2fd40|
|572.724843|0x90040193|0x403d|16B `05003d40130000800080000001000000`|未审计|+0x2e2fd40|
|575.722843|0x92840747|0x33d|8B `0d203d0308000180`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|
|575.722843|0x92840747|0x32e|10B `0d202e030a0001800800`|同步: send_and_wait_cmp_i +0x2de70a8|+0x2de7264|

新增的 VDF0x429（10B `0d2029040a0001800000`）经 +0x2df2d94 调 send_no_wait_i，0x500（10B `0d2000050a0001800100`）经 +0x2df2df4 调 +0x2de66f4，该入口 +0x2de6880 只发送，正常分支 +0x2de6914..+0x2de6928 直接返回，无接收；两者虽然被未注册VDF服务丢弃，但均不是新的同步等待。未审计其功能或实现回复。其余表项在AP69已有，包含服务软件回复后续布局/plane/LUT与释放限制调用，不代表全是新阻塞。

## 仍等待的线程与观测边界

- TID319 SeqThreadPool1 最后发送 ADF0x32e/10B、source0x81cf61c2 后进入同queue接收；TID320 SeqThreadPool2 最后发送 ADF0x33d/8B、source0x81cf61c3 后进入同queue接收，caller均+0x2de7264（send_and_wait_cmp_i）。本轮仅被动保留栈，没有深挖或修改两条ADF。
- TID334 已无未回复的同步VDF请求。snapshot1记录其 S/futex_wait；这是内核睡眠快照，不能据此判定新的协议阻塞。TID322也记录 S/futex_wait，但之后继续发送布局/plane/LUT与释放限制，不能将早期快照说成最终卡死。
- snapshot2/3未再捕获匹配im.elf maps的进程，退出原因未证实；因此上述ADF为最后观测等待点，而不是通过末尾进程存活验收的线程状态。运行器的qemu_exit=0是宿主有界收尾，不是guest正常关机。
- 除0x429/0x500外的新UIPC差集含TID334到0x5503e0/tag0x300f6、TID230到0x808261c0/tag0，以及TID322到0x9059000e/tag0x81cf61c0；完整记录在摘要。后两条及其等待语义未审计，不能声明新同步阻塞，交Lead决定。

## 复核入口

- [80秒运行原回执](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap70lcd-f61554d9/receipt.json)、[serial](../../work/fx3-vm-20261101/menu-repair-01/runtime/runs/ap70lcd-f61554d9/serial.log)。
- [运行摘要与完整时间线](../../work/fx3-vm-20261101/menu-repair-01/runtime/lcd-osd-ap70-run-summary.json)。
- [宿主ASan/UBSan](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/lcd-osd-transport-host-check.json)、[v25构建](../../work/fx3-vm-20261101/menu-repair-01/runtime/helpers/fx3-capid-v25-build.json)。
- [原调用者指令证据](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap70-passive-callers-proof.json)、[候选](../../work/fx3-vm-20261101/menu-repair-01/runtime/ap70-lcd-osd/candidate70.json)。

## 2026-11-01 更正

AP70 serial 第20535行已明确记录 `/usr/bin/im.elf: symbol lookup error: /usr/lib/appFw.so: undefined symbol: iCrypt_HasPublicKey`。主进程被动态链接器终止；此前“退出原因未证实”已被本行证据取代，不能把后续无进程快照当作ADF等待状态。原运行日志保留不变。
