# AP 固定地址绑定守卫：客体同字节二进制复核

输入为 [preload-audit.json](preload-audit.json) 中逐一核到**实际 CPIO 成员 SHA** 的 17 个预载 SO；[disassemble_guards.py](disassemble_guards.py) 固定工具与 5 项范围，原始 AArch64 字节/指令在 [asm-index.json](asm-index.json) 指向的 9 个小文件。这里核的是会使用 FX3 `appFw.so` 固定 RVA 的已定位路径；不能据此证明 17 项全部机器码没有其他计算地址写入。源码 SHA、对应行和编译可追溯程度逐项在审计 JSON 中；GPE 有匹配输出 SHA 的原构建记录，其余 16 项未重建编译。

| 预载/实际客体 SHA 前缀 | 二进制控制边（ELF RVA） | FX6 AP 原字结果与失败后动作 |
| --- | --- | --- |
| `preset` `eb556801` | `dlopen` `0x127dc–0x12c0c`；先以 `0x12aa4/0x12ab4` 等比较跳往 `0x12b40` 拒绝，三段 selftest `install` 在 `0x12adc/0x12afc/0x12b1c`，AP 点安装在 `0x12bbc` 以后。`install` 独立范围 `0x132cc–0x13604`。 | 已有固定原字 48/48 FX3、0/48 FX6；首点 AP VA `0x2dca610`、FX6 文件偏移 `0x2dba610` 为 `0x255`。首点不符走 `FX3_PRESET_CONTEXT_BIND_REJECT point=0 reason=original_word`，`dlopen` 返回原 handle；AP 点安装不执行。 |
| `GPE` `30667f76` | `dlopen` `0x26664–0x26ab0`：`0x268bc` `dlsym(Application_System_Init)`，`0x268ec–0x268f0` 比较返回地址相对映射基址是否 `0x16efb90`，不符跳 `0x267ac`；16 字节前缀逐字分支 `0x268f4–0x269ac`，AP 页 `mprotect` 最早在 `0x26a28`。 | FX6 AP 导出 RVA/文件偏移 `0xc0b044`，与旧期望不同，因此走原 handle 返回路径而非 AP 初始化入口补丁。`libgpe` 与 `libObj` 的独立绑定路径仍可能运行，`bind`/自身前缀等另见 `0x25f28–0x26664`；实际软件 GPE 队列/线程若拒绝不能降级忽略。 |
| `timer` `3b828ba3` | `dlopen` `0x11f9c–0x123d8`；四点循环在 `0x121d8–0x121e0` 比较 16 字节，不符转 `0x12398`；目标页 `mprotect` 最早 `0x122cc`。 | 第一 AP 点 RVA/文件 `0x176fb4c` 原期待 `fd7bbaa9fd030091f51300f9f50300aa`，FX6 实际 `f35301a9f30300aaf55b02a9031cf697`。应报 `FX3_TIMER_BIND_FAILED k=0 reason=prefix original_unchanged=1`，四处原目标均不被此路径改写；此前 `dlopen(libObj.so,5)` 的副作用仍存在。 |
| `UI` `54eeed92` | `dlopen` `0x13764–0x13b58`；原字比较在 `0x13874`／循环，错误分支 `0x13a3c`，首个 selftest 安装 `0x139d0`，AP 安装 `0x13adc`；`install` `0x13ca4–0x13fe4`。 | 60/60 FX3、2/60 FX6；首点 RVA/文件 `0x16f2220` 期待 `0xd10cc3ff`，FX6 `0xf9400bf3`。报 `FX3_UI_GATE_BIND_FAIL id=0 reason=original_instruction`，AP 点安装不执行。保留物理 RAM 观察器自检与失败规则。 |
| `media` `179c74c3` | `dlopen` `0x139bc–0x13eec`；对 AP 的 10 组 getter 每项两段 20 字节 `pread`/比较在 `0x13d14–0x13da8`，不符转 `0x13dd8`；全部通过才走 `0x13dc0` sample。`install` `0x13f98–0x14490` 仅由 MediaDetect/Mount 的点路径使用，其原字核验在 `0x13b54/0x13b64` 和 `0x13e48–0x13e68`。 | 首组 ID `0x6db` getter VA `0x293c010` 映到 FX6 文件 `0x292c010`，期望 `00c7029000e014910004449100f02891c0035fd6`，实际 `0500000002000000020000000900000001000000`。预期 `FX3_MEDIA_BIND_REJECT module=A reason=parameter_getter_code id=0x6db`，不设置 `app_base`，不采样 FX6 AP，不修改 AP 指令。 |

以上四条**精确文本**可由 [classify_serial.py](classify_serial.py) 在固定候选 SHA 下归为预期 FX3 诊断缺席；其他 point/id/reason、混合错行、任何真实 loader/符号/OSAL/硬件保护错误仍是首故障。该分类器继承并逐条保留原 `trial_log_v4_mss.py` 的全部失败正则，还额外识别 UI/timer 非预期拒绝。19 个无 VM fixture 覆盖后续非零及同一行重复 loader RC，不以首个 0 隐藏后续失败。

就这五条已定位路径，AP 固定地址写入前都有原字/地址拒绝；**不能推导 FX6 AP 初始化成功、功能性 CAPID/SKD 适配、17 预载全局无写、或任何客体运行结果**。最早可实测阻断仍可能是 glibc 重定位/符号、原硬件/IPC 保护、或媒体/GPE 的其他路径；以唯一运行者下一次只读回执为准。
