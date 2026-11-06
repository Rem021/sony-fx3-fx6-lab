# FX3 7.02：普通应用的 NIN 启动入口与完整 AP 符号盘点

2026-10-27。**本轮找到普通应用侧的动态认证启动入口：`libObj.so` 注册的事件回调会在限定状态下查找 `libsencore.so` 的 `NinThread`，再交给线程创建封装。** 这条调用链包含未导出的局部函数，单搜命名校验函数会漏掉它。

它仍不能直接证明当前 MSC USB 会话选择了哪个接收器、实际加载了哪份模块，或初始摘要该用前4B还是完整512B。阶段145提供者的算法选择没有被擅自改动。没有运行原生 Sony 代码、Unicorn guest 或相机协议；一次描述符权限保持消耗，实机放行不变。

## 官方镜像范围盘点

[inventory_handlers.py](inventory_handlers.py) 先校验既有 Ext2 读取器与完整 `nflasha15.img` 的固定SHA，然后遍历797项普通文件；532个不同 inode 是 ELF，另265个为非ELF。扫描每个 ELF 的 `.dynsym` / `.symtab` 和依赖，保留路径、inode、大小、SHA、架构与命中符号。

54个 ELF 命中本轮 NIN、senser、认证或 SHA/EVP 摘要名称规则。命名的 `NinThread`、`xxhop`、`xxstep` 只在 `libsencore.so` 中命中。**这不是“其他文件没有认证实现”的证明**：剥离的局部名称、内联实现、数据驱动调用、其他分区、RTOS及ROM均不在这个符号检索结论内。

完整范围及规则见 [AP-handler-inventory.json](AP-handler-inventory.json)。没有将532个文件都提取成新副本；只将下一条调用链所需的原 `libObj.so` 作为数据提取到本阶段 work，SHA为 `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae`。

## 原 `libObj.so` 的入口

[audit_normal_entry.py](audit_normal_entry.py) 静态读取导出的 `senser_init`、`senser_res`、`senser_sus`、`udtr_senser_init` 四个完整函数。`senser_init` 的一个分支调用 `sens_adjCmd_init`，再进入局部函数；另一个模式走不同启动分支。因此不能只凭函数名将所有路径都叫作 MSC 初始认证。

[audit_dynamic_nin.py](audit_dynamic_nin.py) 使用原 `.eh_frame` FDE界定局部函数，审查12个完整函数及24项精确指令事实：

| 原件位置 | 静态事实 |
|---|---|
| `senser_init` VA `eaa04` 的非mode1分支 | 经 `ea54c` → `ea4f4` 调用 `senif_init(1, …)` |
| GOT `2628d0` 及回调表 `2646c8` / `2646d0` | 三项原 RELATIVE重定位共同指向事件回调 `ea128` |
| 回调 `ea128` | 仅处理事件1且内部状态不大于1，保存传入对象，取锁并调用 `eb900`；实际锁/线程行为未执行 |
| `eb900` → `eb794` → `ec570` | 请求打开名为 `libsencore.so` 的库；仅证明请求的basename，未证明真实解析路径或运行时模块身份 |
| `eb900` → `ec5bc` → `dlsym` | 请求符号 `NinThread`，再经 `ec3f4` 交给 `pthread_create` |
| 普通 dispatcher线程 `ea1dc` 的模式0分支 | 另经 `eb7f4` 动态调用 `senser_normal_mode_start`；此分支不与直接NIN启动混为一条路径 |

见 [dynamic-NIN-route-review.json](dynamic-NIN-route-review.json)，包含完整反汇编、每函数SHA和原重定位。第一轮11函数结果保留在 `before-library-basename-review`；补上原 dlopen封装和库名字符串后形成当前12函数结果。执行脚本副本对应当前源码。

## 对算法适用性的影响

阶段141已经用原 `libsencore.so` 验证完整512B挑战加轮材料的服务摘要，但没有证明此次 `libObj` 路径在当前 MSC 状态下的动态模块、`NinCooperator`虚表、接收/发送函数与传输对象绑定。库basename相同不能单独补齐这些运行条件。

本轮把“初始处理者在哪里”收敛到了普通应用的事件注册与动态NIN入口。下一步应追 `ea128` 保存的传输对象、`2ce108` 一带协作者对象的构造/虚表和收发函数，再与 `senif_init` 的实际注册来源连接。没有用名称、代码存在或一次可达的静态分支，替代实机认证接受或前4B算法证明。

## 公开线索刷新

本轮GitHub公开 issue搜索返回16条，原JSON与URL/SHA保留在 `public-issue-refresh`。三个评论API请求遇到403限流后，改用网页读取 #715 / #504，没有使用账号凭据或执行教程。来源与适用范围见 [public-source-review.json](public-source-review.json)。

- [FX3A #715](https://github.com/ma1co/Sony-PMCA-RE/issues/715)：作者2026-06-09报告在2.02上通过调整Mac依赖环境完成PAL/NTSC修改；没有描述改动摘要算法。作者对失败原因的解释未通过受控实验验证。它不是经典FX3 7.02、固件互刷或独立救砖证据。
- [FX3/FX30 #504](https://github.com/ma1co/Sony-PMCA-RE/issues/504)：2024年的语言修改教程未提供经典FX3 7.02验收；2026-08的FX5留言是询问，不能算成功案例。
- [REA #3027](https://github.com/morluto/rea/discussions/3027)：2026-10-13提出FX3 7.02电池行为逆向需求，所阅页面无实现评论，不能当作已可用固件。

目标仍是实际1080p29.97 HEVC MAIN及对应同机恢复、独立救援、冷启动和长录等完整16项要求。本轮没有新增USB、认证、驱动、文件访问或刷写；仍未达到可刷真机条件。
