# 固定 FX3 平台中 FX6 Image：`/init` 第 79–115 行审计

**本轮最深运行证据：原 FX6 内核加载固定 CPIO 中 `devno.ko`、`osal_utm.ko`、`osal_uipc.ko` 均返回 `insmod RC=0`。** runtime owner 的 `fixed-fx3-c72ee0b9` 2.515 秒回执 SHA `c37ad1d014d90fd3311722eec1ff025468aeeccc1001d91456bd06cf6b278ceb`、串口 SHA `034552e396f4dbd49aa55e85fb931272d009e41cf7c0a413d85b373b9c7b8536`；PID 68544 已回收、双锁释放。串口最后到 `/init` 第 79 行 `FX3_PROC_MODULES_BEGIN`，**没有** `/dev/uipc` 节点确认、LDEC、Backup、CP、AP 功能结果。返回 0 只说明这三个原模块的装载入口返回，不说明队列/硬件工作。

[`audit_pre_cp.py`](audit_pre_cp.py) 从固定 CPIO SHA `eaef24b2fe9405fb48bc7823069ad16162cd67c46e004ed6660f761fc16d230d` 提取下面四个实际成员，逐字节核对本地编译输出及固定构建回执/源码；只读固定 DTB SHA `b6f9f4c04d0da101565d67244629a0ad7a3954c8af004f353c16ae0c8b499de7` 的 memreserve map。详见 [`pre-cp-audit.json`](pre-cp-audit.json)，脚本输出 `PASS_STATIC_PRE_CP_ROUTE_WITH_RUNTIME_FIRST_ORIGINAL_MODULES_ONLY`；没有执行这些 simulation 程序。

| `/init` 行 | 实际程序及 SHA | 已闭合代码边与内存写入 | 首次运行未知 |
|---|---|---|---|
| 79–87 | 原 `cat /proc/modules`、`/proc/devices`、`/proc/udm/drivers`、`ls /dev/uipc` | 第 86 行 `-c /dev/uipc` 决定是否进入 simulation；当前串口未到节点结果。 | **第一运行态未知：`/dev/uipc` 字符节点是否存在。** |
| 88–94 | `fx3-ldec-soft103-v1.ko` SHA `dec6285407341319bfe6239a47e434f08b920ec23c6af960d2653c1d061c02df` | 固定源码 SHA `6c026aeb...`、构建回执 SHA `2cb96617...`；原 `.text+0x4e8` 重定位读 `devno.ko` 的 `udif_devnodes`，`+0x5c4` CALL26 到内核 `udif_cdev_register`。固定 devno 表 `.data` 第 5 项（文件 `0x400`）为 `ldec`, type0, major251, minor205, count1；名称指针原重定位指向 `.rodata.str1.8+0x48`。`init_module` 校验该项，再注册 cdev，不在 init 中写硬编码内核 VA。 | FX6 `udif_cdev_register` 完整函数与 FX3 字节不同；返回与 cdev 节点均未运行验证。 |
| 95–98 | `fx3-ldec-ioctl103-test-v2` SHA `c6e792379e8adefd221f172a379593adfdf37141f920292a1abcd25f1223a4ab` | 固定源码 SHA `c0072036...`；通过 `/dev/mem` 映射 `0x41d300000` 的 **1 MiB** 测试区并填哨兵，`/dev/ldec` ioctl 3 个已有夹具；module 先校验 p32/长度/解码，再写目标并读回，失败尝试回滚。固定 DTB 原 memreserve 中有该完整 1 MiB。 | `/dev/mem` 映射、FX6 的 `arch_p32_to_p64`/`arch_phys_to_va` 语义及实际读回未验证；这仍会写 guest 预留 RAM。 |
| 99–113 | `fx3-file100-observer-v2` SHA `044d08549217523c645035e02ae74b1e76b73db17a61d13b0ff4ecd05a3987e0` | 固定源码 SHA `288f6946...`；`/setting/Backup.bin` 以 O_RDONLY 双读，只将副本写到 `0x41d400000` 起 **3 MiB** 独立观察区，另在 `/tmp` 写 PID ready 标记。DTB memreserve 精确覆盖 3 MiB；前 4096 B 初始化零，`h[6]` 的退出脚本触发值在此阶段没有生产者。 | Backup 文件读取、物理映射、PID ready 均未在 FX6 内核下运行验证；不等于原 Backup/CP 同步。 |
| 114–118 | `fx3-cp-backup-reset-v1.ko` SHA `f4d7a1fa048d3548840fb2b9dd91e9538b19a34e48089a01ee466c02d3c277ca` | 与 v5-native101 构建逐字同一；原入口要求 `pcidma_transfer_async=0xffffff80083220c8` 并 patch 首16B，FX6 Image 原导出为 `0xffffff8008322f70`。完整合同见父目录 [`firmware-side-contract.json`](../firmware-side-contract.json)。 | **条件性拒绝**：若运行至此且原 FX6 lookup 返回其链接地址，应返回非零；尚无自然串口错误回执。绝不放宽门或改 helper。 |

三个前序 simulation 二进制源码及其已固定构建产物中，未发现未守卫的 **旧 FX3 内核绝对 VA** 写入、热补丁或跳转；LDEC 初始注册走 ELF 重定位导入，后续物理写入限于上述两块**已有 DTB 预留** guest RAM。这个范围判断不覆盖内核导出实现、运行态映射和任意外部写入；它也不是硬件可运行验收。原 LDEC 源另列 `0x410524000..0x410e64000` 的 GPE 池，但第 95 行自检请求只选择 `0x41d300000` 的独立区。文件观察者的退出脚本只有观察区 `h[6]==0x100c1ea9` 后才执行，第 99 行启动时该页已清零；不以此推断未来 AP 永不触发。

## 给 runtime owner 的单次观察规则

只在现有 runtime 独占窗口、完成其 FX3 关机诊断与操作后，审当前 [`fixed_runner.py`](../fixed_runner.py) SHA（运行前须重新核对）并调用 `python3 fixed_runner.py --check --mode pre-cp-first-result`。该模式在运行前核对固定平台候选、[`pre-cp-audit.json`](pre-cp-audit.json) SHA、固件侧合同 SHA；`--check` 不取锁、不启动 QEMU。`pre-cp-audit/host_selftest.py` 的 7 个阳/阴性标记及不完整串口行检查已离线通过，回执 [`host-selftest.json`](host-selftest.json)；不代表 guest 执行。

**排队后的唯一运行命令**由 owner 审阅再执行：`python3 fixed_runner.py --run --mode pre-cp-first-result --seconds 180`。沿用原双锁、同一个冻结 QEMU/virt/DTB/CPIO/Backup 和仅 Image 替换，拒绝占锁，限定自身子进程和 180 秒；不改 guest 或设备。host 轮询按顺序遇内核 panic/oops、CPUSET_NOT_READY、原模块非零返回、`/dev/uipc` 缺失、LDEC insmod/自检失败、file observer ready 失败、CP helper 任意 `FX3_BACKUP_CP_INSMOD_RC` 立即结束；若意外出现 CP RC0，则记录 `unexpected_cp_helper_success` 并停，`FX3_UTIMER_BEGIN` 是 AP 前护栏，`FX3_AP_NATURAL_BOOTIN_BEGIN` 是越界警报。CP 开始后 40 秒仍无完整返回行也停。**串口轮询不是 CPU 断点**，不能保证无指令越过标记；任何 AP 标记均判越界，不得把该轮用作符合“未执行 AP”的证据。原 CP helper 的地址拒绝门保持不变，因此其自然成功与现有静态证据矛盾，须先查错，不继续 AP。

本轮不自行启动 QEMU、不占锁，也不把 FX3 原模块 RC0 推成硬件、队列或电影功能完成。下一轮先看第 86 行 `/dev/uipc` 字符节点与第一条自然错误；若停在 LDEC 的 FX6 内核导出或物理映射，先做对应接口原字节审计，再决定是否继续，不反复运行到已知 CP `-7`。
