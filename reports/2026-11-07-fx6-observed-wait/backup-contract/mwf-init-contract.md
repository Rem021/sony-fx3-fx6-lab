# MWF_Init 固定版本调用契约（2026-11-07）

**结果：实际 `libMWF.so` 的 `MWF_Init` 不消费 incoming X0/W0，也没有可用于判成功的整数返回契约。它是原 IM descriptor 管理的显式初始化入口；不能把这一结论推广为所有 init 都无参，不能把 IM loader 的返回0当成 MWF 内部成功。Kiki 的正常扫描顺序可确认，功能完成依赖尚未证明。** 本轮没有调用任何供体函数或运行 VM。

自写 [inspect_mwf_init_contract.py](inspect_mwf_init_contract.py) 已 PASS，[mwf-init-contract.json](mwf-init-contract.json) 保存哈希、少量指令事实、PLT 绑定、descriptor 字段和局限。

## 入口与入参

固定源为 FX6 `libMWF.so`，353120B，SHA `3c9666c49bde90076cf69af13295dc07e585d87c51a27ecaf7f1926df87d1782`。

- 导出 `MWF_Init` VA `0x27e74`、大小4B，仅尾跳到 PLT `MWF::Initialize()`，真实函数 VA `0x27d68`。
- `0x27d68` 第一条是 `adrp x0,#0x65000`；下一条从该页读取 guard。因此 incoming X0/W0 在任何读取前就被覆盖，不能解释为配置字符串、descriptor 指针或模式参数。
- 这是该固定二进制的事实；未恢复原厂头文件，不据此声称其它版本/其它入口也无参，尤其不能删掉通用 IM 参数路径。

最小 ABI 模型是“此版本不依赖 incoming X0，不向管理器提供可消费的业务返回码”。如果实现入口观察器，应保留原寄存器/异常/errno 转发，避免为通用入口杜撰统一 C 原型。这里没有编写或集成调用补丁。

## 返回与状态

`MWF::Initialize` 在 `0x27d80` **先设置 guard `0x65c89=1`**，然后才调用 MwfCommon、Monitor、线程/消息接口、资源关系等初始化。它不是“初始化完成才置位”的 ready flag，也没有本轮证明的并发重试/失败恢复契约。

guard 已非零时 `0x27e08` 直接 ret，此时 X0 仍为运行载入基址加 `0x65000`。正常首次路径则在 `0x27dec` 尾跳 `InhInfo::Initialize()`，没有统一设置 W0 为成功码；异常清理路径会继续 `_Unwind_Resume`。**因此不得检验调用后 W0==0 来认定 MWF 成功，也不得以 guard==1 替代完成回执。** “void-like 初始化入口”是基于返回行为与调用方的 ABI 推断，未恢复原声明的返回类型。

## IM descriptor 与两条调用路径

实际 `libIMDB.so` 为79728B，SHA `a088ef303793497a443e89d6de4c8f12e07ec791c945f54e2dc1b52cd42db896`。descriptor 步长72B：

| 偏移 | 本轮证明的字段 |
|---|---|
| +0x00 | u32 类型 |
| +0x04 / +0x08 | u32 flags / target mask，用于扫描过滤 |
| +0x0c / +0x0e | u16 module ID / loader选择字段；不再把整个4B笼统当单一ID |
| +0x10 / +0x18 | 库名 / init 符号字符串指针 |
| +0x20 / +0x28 / +0x30 | 后续生命周期字符串槽；本轮只保存原值，不为所有类型恢复统一原型 |
| +0x38 / +0x40 | 参数路径可选择的两个指针槽 |

MWF 项索引32、VA `0x1f270`，类型 `0x20000002`、flags1、target `0x7fffffff`、ID151、loader选择字段0；库/入口是 `libMWF.so / MWF_Init`，+0x38/+0x40 都指向空字符串。**这两个槽存在，不表示此类型的 MWF 入口会接收它们。**

实际 `im.elf` 的类型派发为：

1. `0x20000001..0x20000003` → `0x405f5c`。在 `0x406004` 做 dlsym，在 `0x40602c` 执行 `blr x20`；调用前没有从 descriptor 参数槽设置 X0。随后直接跳到 `0x405fd8` 令 loader 本地状态 W19=0，保存 DSO handle，**不检查被调者返回寄存器**。正常 dlerror 分支会在调用前留下 X0=0；跳过该检查的分支可能留下符号地址。固定 MWF 覆盖 X0，因此不依赖这种残留。
2. `0x20000004` → `0x405e24`。题述 `0x405f0c` 是 dlsym，真正函数指针调用在 **`0x405f44`**。`0x405f34` 从 descriptor+0x38/+0x40 加载两个值，按 manager 全局 flags 的 bit14 选择 X0：置位取+0x38，否则取+0x40。此路径必须保留参数槽与选择条件；不能按 MWF 的行为改成全局无参调用。

loader 的 -1/-2 对应装载/符号处理路径；0是其本地装载调用路径结果，不是 init 的业务状态。

### 真正的 manager 完成记录

新模块状态正常路径在 `0x4064a0` 调用上述类型派发，`0x4064a4` 取得 **loader 的本地状态**。正常返回0后，`0x4064c0` 保存 handle 到模块状态对象+0x20，`0x4064c8` 写数字状态2到+0x28，随后释放模块与全局信号量。非零结果转入原错误/状态回收路径。

这比单独 dlopen 多了原厂状态和互斥所有权；但状态2仍只是此处管理器状态，不能自动解释为全部异步线程、回调、硬件和 UI ready。若恢复生命周期，应保留 descriptor 过滤/阶段/状态/信号量路径，并独立观察关键对象与服务完成；不能仅手调 MWF_Init 再伪写状态2。

## Kiki：顺序与完成依赖分开

复用已有生命周期表扫描结论，本轮补了同步派发返回边：Kiki 项索引29、类型 `0x20000001`、ID272；MWF索引32、类型 `0x20000002`、ID151。相同正常启动区间中，两项通过 enable/flags/target 过滤且走新状态路径时，扫描器在 `0x4065f0` 同步调用派发函数，返回后才在 `0x40660c` 递增到下一descriptor。因此在这些条件下，**Kiki init 入口返回先于后面的 MWF init 派发**，不是仅依据表的物理排列。

这个“入口已返回”仍不足以证明 Kiki 功能完成：实际 `KikiLogGenerator_init` VA `0x3a0c` 设置 W0=1，调用其 `init_proc` 后尾跳后续操作；`init_proc` 的 open 返回负值仍会继续后续注册，已检查的 ioctl/注册调用没有在此处构成成功门。不能由管理器继续扫描就推出 fd、ioctl、回调和异步服务全部就绪。

`libMWF.so` 没有 Kiki 命名动态导入，也没有 Kiki 的 DT_NEEDED；已检查的 MWF 初始化入口没有直接 Kiki readiness 测试。这只是不支持“已证明直接依赖”的证据，不能排除经 Monitor、消息、运行期符号或其它共享服务的间接依赖。**本轮没有足够证据宣称 MWF 必须等待 Kiki 功能完成，也没有足够证据宣称可以任意倒序或跳过原厂顺序。** 恢复原 IM 管理顺序有事实依据，额外手工 Kiki 完成屏障则需要生产者/消费者证据。

## 哈希漂移与交付边界

当前实际 donor `bin/im.elf` 是40920B、SHA `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec`；旧 `deep-init/lifecycle-order.md` 写的是同大小 `2838e5da0fcaf7e8db543f0bd33a9e73411143be293d4509b7fa3edcc26ab772`。尚未解释差异。本轮所有 IM 指令断言明确绑定当前哈希，不把旧哈希的历史结论默认为当前原件一致。

quick audit 的 `latest-mwf-runtime.md/json` 已按父 agent 白名单正式复制并更新 [files.json](../../reports/2026-11-07-fx6-observed-wait/backup-contract/files.json)，原事实未改；本补充仅输出本 work 目录。未改 shim、候选、供体或管理器状态，未运行 VM/相机，未 Git/sync。
