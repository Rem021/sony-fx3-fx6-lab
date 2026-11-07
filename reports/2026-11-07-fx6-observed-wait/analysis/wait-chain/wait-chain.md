# 已确证等待：cold-boot future 的执行器被现有 NOP 删除

**当前 AppFw 等待的是 `model::model_future::wait()`，其对应生产者是原厂 `model::sequence_cold_boot`。295 的 `+0x12d825c` NOP 恰好删除了执行该生产者的原生45线程池创建调用。** 这是比泛指 MWF/硬件服务缺失更直接的解释；严格说属于自行删除执行器造成的 future 饥饿，现有证据没有证明两把互斥锁形成锁环。

这里绑定完整 serial SHA `5f4e7e5fd909dd6888df5ae2b0506a485274f9aa6a9c2193106bcff7616feafa`，分析读取的是 final `snapshot.json` / `resolved.json`，不是partial记录。快照采集成功与120秒运行结束，不等于初始化、菜单或实机成功。

## 等待条件与通知者

实际 CPIO 的 appFw SHA `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`。所有读取通过该ELF的PT_LOAD把VMA映射到文件位置，未把VA直接当offset。`+0xc09de8` 所在运行页曾因原patcher变为RWX，映射解析不要求运行PF_W与原ELF相同。

实测TID224链为 pthread_cond_wait `+0xd5ec` → libstdc++ condition_variable::wait `+0xb3610` → appFw `+0x1acd988` → `+0x12d9dec` → `+0x12da024` → `+0xc09de8`。`+0x1acd874` 引用原厂断言身份 `model_mutex.cpp` / `void model::model_future::wait()`，不是OSAL队列接收。

`+0x1acce10` 构造promise：byte+0清0，int+4清0，+8保存新建condition_variable指针；`+0x1acce84` 产生future，携带上述ready/result/condvar三个指针。`+0x1acd874` 在全局model mutex保护下检查ready，等待自身condvar；当前确证停在 `+0x1acd984` 调用返回点 `+0x1acd988`。有model-lock递归深度时，它会把执行权交给ready队列下一线程或清空当前owner，再等待，符合允许另一个worker运行的协作锁协议。

真正fulfill函数是 `+0x1accea8`：取得model mutex，写promise ready byte=1，解锁并对promise的condvar调用 `notify_one`。另一个 `+0x1accef4` 版本还写int结果，但本次cold-boot链调用前者。没有理由伪造通知或改ready。

## `+0x12d8174` 准备并等待什么

外层 `+0x12d9fc8` 对model API id `0x3b16` 建立交易和model-lock。`+0x12d8174` 先设置model状态及接受请求标志：`+0x12d8248 → +0x10f6208` 把请求接受byte `0x4da6538` 设1。随后原调用序列包括worker、infrastructure初始化和model pool；大量model初始化赋值完成后，函数尾部才建立本次promise并启动cold boot：

| 步骤 | 已核对链 |
|---|---|
| 建promise/future | `12d9dbc → 1acce10`，`12d9dc8 → 1acce84`；promise在该函数FP+0xb0，future在FP+0x210 |
| 生成异步请求 | `12d9ddc → 10fa3cc → 10b9cb8`；command type=`0x2d`，携同一个promise指针 |
| flush待处理请求 | `12d9de0 → 10f727c`；本请求单项vector，dispatch表 `29b9318 → 10b6fe4` |
| 建原生job | `10b6fe4 → 1e2d2c8 → 1d72e50`；promise复制到job+0x10 |
| job身份 | ctor的vtable `2ec5ee0`，RTTI=`model::sequence_cold_boot`，execute=`1cd826c` |
| 原生队列 | `1e277e8` 入指定worker队列并notify worker condvar；type0x2d在 `25a1560` pool映射中等于index0 |
| 真正完成通知 | cold-boot execute成功尾部 `1cd86a8` 取job+0x10 promise，`1cd86ac → 1accea8` fulfill+notify |
| AppFw等待 | `12d9de8 → 1acd874`，正是实测savedLR `12d9dec` 的来源 |

外部服务可能阻塞cold-boot execute内的某个阶段，但295当前在更早的层次已经删掉执行它的线程池。

## 五个NOP中哪一个解释本次等待

实际295 shim为79504B，SHA `c58b6509e451a32474a6e2ace7c680a58427a5b685eaf27ece9a51153c2a3f45`。直接解析其符号 `fx6_patch_blocking_calls.offs`，VMA/file offset均为 `0x2ed0`，确认五个偏移。完整serial五行均记 `mprotect=0`，所以不是只依据漂移的/tmp源码。

| NOP点 | 原生目标 | 对本次等待的意义 |
|---|---|---|
| `12d825c` | `1d96370` | **直接删除所需执行器**：循环创建45个worker，index0..44，对应线程元数据id6..50。entry从原ELF重定位指针取 `1e25354 → 1e2518c`，worker取job后调用vtable+0x10，正是cold-boot execute槽。此次枚举只有217/224/225/226，没有该pool。 |
| `12d824c` | `1a6ee10` | 另建metadata id0x3e worker，entry `1ac2b34 → 1a76dd8`；它是另一条model命令执行链，不能与上面45线程pool混同。 |
| `12d8254` | `20ed13c` | 删除70项infrastructure初始化。即使恢复pool，这仍可能使cold boot执行后等待真实服务，属于后续待证依赖。 |
| `12d8250` | `1a5a230` | 进行model状态准备，未证明是当前promise的直接通知者。 |
| `c09e50` | `c09c14` | App定时器启动位于当前 `c09de4` 初始化调用返回之后；当前尚停在前者，不能用尚未到达的timer解释本次future等待。 |

## 结论强度与下一步

已闭合：实际等待身份、promise传递、type0x2d job、cold-boot RTTI/execute、真实fulfill和执行它的pool，以及现有shim删除pool创建的准确调用点。**优先修复自身删除的执行器**，而不是改ready、notify或伪造消息/成功返回。

仍未闭合：运行内存中五个NOP字节没有逐字节readback；还未做只恢复pool的反事实运行；没有证明cold boot能在其余infra NOP/硬件缺口下完成。恢复 `12d825c` 是有明确生产者依据的最小修复实验，不代表恢复所有启动依赖。MWF初始化入口/契约是独立问题，当前没有证据把它自动认定为此future的直接根因。

GCC维护者的 [condition_variable实现](https://github.com/gcc-mirror/gcc/blob/releases/gcc-6.3.0/libstdc%2B%2B-v3/src/c%2B%2B11/condition_variable.cc) 将wait与notify分别交给底层cond_wait/cond_signal；这支持区分等待原语与业务完成条件。具体Sony ready与producer身份均以本轮实际ELF指令、RTTI和实测栈为准。

复跑：`python3 -B work/fx6-wait-snapshot-20261107/analyze_wait_chain.py`。脚本只读固定CPIO/ELF/final日志，输出结构元数据至本work目录，不启动VM，不导出固件payload，不改候选。
