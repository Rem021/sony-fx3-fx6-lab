# FX3 内核 + FX6 上层：冻结启动包独立复核

2026-11-03。**依赖文件存在性通过；程序和辅助库兼容性仍未通过。** 本轮直接解析固定 `guest.cpio`，没有运行目标程序、构造混合载荷或修改 FX3 平台。

## 纠正首轮目录投影结论

`hybrid-assessment/README.md` 与首轮回执的“固定 FX3 guest 缺 libopus/libSoundTouch”结论不成立。目录投影不等于实际启动包；冻结 CPIO 中两库实体及 SONAME 符号链接均存在：

| 请求库 | 实际客体文件 | SHA256 |
| --- | --- | --- |
| libopus.so.0 | /usr/lib/libopus.so.0.8.0 | 473c7182bfd47bbbcce4e377015bc9d6bbef554c4eda287ba6a31ecc34f4579a |
| libSoundTouch.so.1 | /usr/lib/libSoundTouch.so.1.0.0 | d4abdc58ae1857d46791b7f8d3ebf0d822f03c5a8d343f3d975a98f0ff40522e |

[audit.py](audit.py) 对 SHA `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d` 的 CPIO 做独立 newc 解析，将全部 **1,140** 个成员的长度和哈希与冻结审计交叉核对，按 `/simulation:/usr/lib:/lib` 解析实际符号链接。以原 FX6 `bootin.elf`、`im.elf`、`appFw.so` 为三个根、沿固定 FX3 库递归 `DT_NEEDED`，三者均无缺失路径。没有借用 FX6 更新器库，也没有新增库。

这只证明声明依赖的文件存在。不是 glibc 动态链接器的运行结果；符号逐项版本、全局插件、初始化顺序、私有 ioctl/IPC 和自然装载路径仍需评估。后续任务应使用实际 CPIO 成员，不能按局部投影缺件来规划替换。

## 辅助库确实绑定 FX3 程序布局

固定 CPIO 的 `/simulation/fx3-preset-context-v2-screen.so` 名称仍是 v2，但实际字节 SHA `eb55680196806fb86958d632c6aed939eae91aa1ef928690a4a7d21d6a76c170` 与本机 **v6-save102** 构建产物一致；不能按文件名推断源码版本。已核对构建回执、源码 SHA `32bb3b5ae43ddab667c655941784daf028f26ce4c9ce6cca7e91268c4bb72663`、实际预载环境及 `FX3_DISPLAY_OBSERVE=passive-v1`。

该版本源码第 44 行在安装探针前检查 48 个原指令字。按两份原始 ARM64 ELF 的 **PT_LOAD 虚拟地址映射** 读取：FX3 48/48 匹配，FX6 0/48 匹配。第一个检查：

| 相对 VA | 预期字 | FX3 文件偏移/实际字 | FX6 文件偏移/实际字 |
| --- | --- | --- | --- |
| 0x2dca610 | 0xa9bb7bfd | 0x2dca610 / 0xa9bb7bfd | 0x2dba610 / 0x00000255 |

若 FX6 `appFw.so` 成功经该 `dlopen` 包装器并满足环境条件，固定源码会在第一项返回 `FX3_PRESET_CONTEXT_BIND_REJECT`，不会安装此组探针。**这是原字节/构建来源支持的条件推断，没有新的客体拒绝日志。** 它是观察辅助库，此处返回并不等于原应用一定退出；其他预载库及更早的装载顺序也未验证。不能把这个条件拒绝冒充混合系统的首个运行失败。

下一阶段应逐个审核实际预载辅助库及运行器对 FX3 标记的依赖。保持冻结版本不动，不通过删除校验、挪动地址或绕过错误让 FX6“通过”。若固件侧兼容载荷需要额外适配，必须列为显式软件差分，先区分功能依赖与诊断依赖。

## 复现与边界

在项目根执行：

```sh
python3 work/fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/coordinator-hybrid-review/audit.py
```

输出 [receipt.json](receipt.json)。仅写本目录审计回执；不执行 ELF、不改 CPIO、不访问相机、不启动 QEMU。完整 FX6 系统、FX6 菜单、AV/CP 和影像功能均未运行验证。

官方背景：[Linux 内核接口说明](https://cdn.kernel.org/doc/html/latest/process/stable-api-nonsense.html) 区分用户态系统调用接口与不保证稳定的内核内部接口（2026-11-03 核查）。这支持分开评估应用与驱动，**并不能证明 Sony 私有接口或本混合移植兼容**。
