# FX3 原进程入口、preload失败与冷启动条件

2026-10-29。继续恢复优先目标。本轮取得原 rootfs 的动态装载证据，完成 **5组原加载器局部指令检查**，并补全 AP 的进程启动候选盘点。没有认证、文件传输、模块上传、相机操作或刷写；完整 Linux／ld.so 启动和实机恢复未测试。

## 本轮改变了什么

- FX3原 `/bin/sh`、`/bin/date` 都是指向 BusyBox 的镜像内软链接。BusyBox为动态ARM64程序，解释器 `/lib/ld-linux-aarch64.so.1` 指向镜像内 `ld-2.25.so`，不是“静态shell不读preload”的情况。软链接仅在镜像内解析，未在Mac创建或跟随。
- 原 `fstab.ext` 声明 `/etc` 和 `/var` 来自可写 `/dev/nflasha10`。原 `init2` 随后挂载 tmpfs 到 `/tmp_wbshd`。因此社区的 `/etc/ld.so.preload` 指针修改涉及持久文件，不能写成整个方案都只改RAM。
- 原加载器有非致命的 preload 错误消费分支。它为“真正干净启动后RAM模块消失、指针文件仍残留”的处理提供了局部代码依据；没有因此证明普通关开机可恢复、WBI不会恢复旧RAM或固件变砖可救回。

## 原件与候选盘点

[最终盘点](launch-inventory-v2.json)重新核对532个AP ELF，29个文件含精确的 fork／exec／system／spawn 等动态符号，共103处直接分支候选。每个候选记录解码字节、4字节数据间隙及符号归属；间接调用、原始系统调用、其他分区或动态拼接仍不包含在完整性声明内。候选存在不代表能从USB进入，也不代表参数可控。

首版在线性反汇编遇到嵌入数据后停止，少计部分ET_EXEC调用，原[脚本](inventory-initial-stop-on-data.py)和[结果](launch-inventory-initial-stop-on-data.json)完整保留。最终版逐个对齐跳过不可解码字，并验证覆盖全部.text；77处变为103处。最终版是本轮权威盘点，首版的零命中不能作“不存在”证明。

rootfs镜像SHA256：`ceca23d253350e65df9c7c976f06e545ad41a2d8f272d28fc1e73fcc576ddba7`。
原加载器SHA256：`90b4fe734ba7faa08d4591b1363bff478e7bde399a821fc0b2d021c062a58a9a`。
BusyBox SHA256：`c3297a7086efe9a001c39fa98d74d125992cf3225cf353ab6ff2238d827c7799`。

## preload错误消费者：5组局部原指令检查

[证据](preload-recovery-review.json)包含三份启动文件原文、原加载器函数148字节的指令与SHA，以及三个原调用位置 `0x3ab0/0x3bbc/0x3c14`。原函数位于 `0xb00`，其 `_dl_catch_error` 的PLT身份已核对；与[glibc 2.25维护者源码](https://github.com/bminor/glibc/blob/glibc-2.25/elf/rtld.c#L589)的错误分支相符。运行的是Sony原镜像指令，未使用上游重编译来冒充。

| 显式环境夹具 | 原函数观察结果 |
|---|---|
| 已捕获ENOENT／无效ELF／EACCES，三组 | 发出警告，正常返回0 |
| 新对象已加载，计数增加 | 正常返回1 |
| 已加载对象重复请求，计数不变 | 正常返回0 |

`_dl_catch_error`结果和诊断输出接收器是夹具，真实文件查找／异常捕获／mmap／初始化器未运行；未把三个错误结果当作真实文件失败测试。原指令不替换，未执行SVC或对Mac装载Sony二进制。

**回退边界**：只支持“已捕获的 preload 对象查找错误不会被这个函数直接升级为进程终止”的结论。不覆盖构造函数崩溃／阻塞，不保证WBI路径清空RAM，更不提供p1损坏后的独立恢复。

## 下一项具体工作

[实施判断](launch-decision.json)保留16项目标要求及所有权限边界。社区固定debug子进程拦截是下一项离线候选研究，尚非可部署路线；原日期触发失败可能修改时钟，fork失败／无超时wait仍有原程序影响。其它29个文件的候选并未被全部排除。

工具[0.4](../../../outputs/fx3-recovery-adapter/README.md)生成的是静态ET_EXEC，不能直接作为LD_PRELOAD模块。后续须补受限ET_DYN与精确子进程guard，验证Sony装载、退出和请求寿命。同时先完成现有同进程原生owner／IOKit通道集成和固定读取准入，使后续实机预检有可审查代码与范围。当前p1同机备份、真实USB服务及G09冷启动/WBI状态仍未取得。

[本轮交叉核对](verification-receipt.json)覆盖5组结果、三个原调用指令及最终盘点完整性。持续目标[active](native-goal-observed.json)，未完成、未放开任何持久刷写；新相机／管理员动作均为0。
