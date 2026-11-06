# generation4 冷启动逐键图像判读

运行：`runs/vmopt-20261103-reload-guest900-641917f7`。`ap102-native-load-readback.json` 证明原生 backup.ko 在 AP bootin 前从 `/setting/Backup.bin` O_RDONLY 读入固定 SHA `92fe4031d552e9a3d8035f852fe40617fc91445c79a8456017b9c40677e4ac8f`；两 bank RAM 与文件逐字节相等且校验有效，没有 host RAM 回放。

- Phase A `ap102-phaseA-before-SETUP.png`：自然待机显示 HD/Fixed-59,94fps/NO CARD 与 AF-C、D-R OFF，未见菜单。下一键 MENU `0x1ab` 检查加载后的语言 UI。
- Step 1 `ap102-step-01-key-1ab.png`：菜单已是 English `Setup / Area/Date / Language`，证明重载后的 UI 语言；右侧值尚在绘制，先只读迟到帧及 RAM/文件字段，不追加键。
- Step 1 迟到 `ap102-reload-language-late.png`：Language 行明确显示 English；只读状态 RAM language=0，原生文件 language `0x8dd85=0`，date `0x9100c=0`，文件有效。启动前 `ap102-native-load-readback.json` 的文件 SHA 为固定 `92fe…ac8f`，AP 启动后观察文件 SHA 已变化（`a7b8…cb8f`，observer generation2），需区分来源与后续自然写入。下一键 MENU `0x1ab` 关闭菜单，静置并回收。
- Step 2 `ap102-step-02-key-1ab.png`：菜单关闭到拍摄待机。距 step2 输入 70.280s 后 `ap102-reload-closed-idle60.png` 仍稳定；同次只读 RAM language=0、原生文件 language=0/date=0、两 bank checksum 有效。冷启动固定副本与原生运行文件只在 `0x20,0x2c` 两个头部字节不同，语义字段未变。停止按键，请求有界正常收尾。
