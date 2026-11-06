# FX6 AP → 固定 FX3 MPR Init 只读观察候选

**阶段：候选源已冻结；获准单轮运行已结束，实测与清理见 [RUN-OBSERVATION.md](RUN-OBSERVATION.md)。** 继承已通过第四次同调用观察的固定 FX3 Image/完整 DTB/QEMU/原 `/init`/17 helpers/Backup/env/三入口 CPIO；不得改参数、返回值、寄存器、客体代码或 helper。`run_mpr_once.py` 复制并局部改造已审的单轮 runner，精确差异见 [`runner-diff.patch`](runner-diff.patch)。仅允许自有进程、私有日志、零按键、观察120秒/总180秒、最多6个已识别原指令停顿；每个 `Z1` 经 `z1` 移除后才执行既有 API16 软件 observer 恢复。失败原样记录，不自动重跑。

## 为什么能早于 MPR 调用取得 AP 基址

此前第四轮 serial SHA `b2d6f86f7b5ce81017c7dd9a7125128d4f8cdb35d85985aa18d990d48f5bfde2` 的第一完整 early `/init` IM maps 在 byte 159706–186877；后续完整 AP/libmpr late maps 才在 byte 1643920 起。早期块没有 AP 或 MPR，不能凭该块猜这两者 ASLR。新观察器先由同 PID IM `PT_LOAD` 得到其 **ET_EXEC bias=0**，在原 IM `0x406284` 对 `0x20000004` 类型调用设第一个断点；然后检查本轮指向的原 IMDB 记录四字、路径 `appFw.so` 与入口 `Application_System_Init`。实际固定 FX3 `libIMDB.so` 中该类型有三项：记录143是 AP，144是 `subapp.so`，145是 `libVssApp.so`；若自然首命中不是 AP，明确 `unknown_record` 停止，不假装唯一。记录匹配后在同 IM/TLS/记录的 `dlsym` 返回 `0x405f10` 读取原 `x0` 导出地址，用固定 FX6 AP `Application_System_Init` VA `0xc0b044` 求本轮 bias，并在当前 CPU 核 AP ELF 头、PHDR、原指令。这个解析发生在 AP 入口调用前，避免晚 maps 零命中和历史 ASLR。真实自然选择是否按记录143先执行仍待运行。

## 最少观察点与身份门

固定原件：FX6 IM SHA `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec`，FX6 AP SHA `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`，固定 FX3 libmpr SHA `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c`。原 AP `0x212f7b8` 机器字 `429fa797` 解码 BL→`0xb174c0` PLT；PLT 载入 GOT `0x2ef1368`，原 `.rela.plt` `R_AARCH64_JUMP_SLOT _ZN3mpr4InitERKNS_11initInParamE`。所有 VA→fileoff/原字由 `test_host.py` 校验，不以单纯符号名匹配推 ABI。

AP 原调用点停住才按本轮 x0=x29+0x20、当前 AP ELF/PHDR/原码核实，并只读完整 `0x290` 输入记录（SHA、hex，非重构）。记录中单独列 `+0x1d0` callback、`+0x268` count、FX3 会误读的 `+0x1f2` u16、FX6 原源 `+0x28a` u16；当前 FX6 Xavcs initializer 的 780/Mxf 保留 1440 是静态路径，实际模式与本次值未知，不能全局改 780。GOT 前值若已经是固定 FX3 `mpr::Init` VA `0xb6844`，先由当前 CPU 原 MPR ELF/PHDR/五个代码字验证，再在该入口设第二断点核同一 TLS 和原 x0 参数；之后可选原 `capidtbl::Init` VA `0x13250c`，最后原 AP 返回 `0x212f7bc` 核同一 TLS/帧、GOT 后值及 `w0`。若 GOT 前仍指向 lazy resolver，不猜 MPR bias：只设 AP 返回断点，后值若已解析再核当前 MPR 身份；此路径**没有 CAPID 断点覆盖，不能说 CAPID 没执行**。若 CAPID 断点已安装而 AP 返回先到，仅说明该同调用时间窗未命中原入口。vCPU 编号不是 Linux TID，初始化期间可有别的 worker 活动；未知 CPU/记录/ELF/TLS/帧一律停止。

## 主机回执与运行条件

`python3 -B test_host.py` 的 6 个 `PASS_NO_QEMU` 测试含原文件重定位/机器字、早期 IM maps 与截断、合成状态机完整路径、错误 IM/回调、MPR 入口后直接返回且 CAPID 已武装未命中、lazy GOT 前未知而后已解析但 CAPID 未武装。合成 `count/u16/w0` 是测试 fixture，绝不写成自然值。父目录 `python3 -B audit.py` 另复核整套固定平台和 18 项已有身份测试。当前候选源码 SHA：`mpr_probe.py` `ad6a5f8df3e6e77a3cde1d129fa515090e95b74a581708e4c11e38c208e86d96`、`run_mpr_once.py` `37033deb235351937666eb960c177076f982b321e04204c10694337489668f7b`、`test_host.py` `e165eefc321aeb96c79b4ac9431e7c879b439b864a19ab2679633c52934125a4`。运行前这些 SHA、卷 UUID、双锁均已核；授权窗口已经消耗，不再执行 `run_mpr_once.py`。静态/合成回执及本轮 `w0=3` 均不代表 MPR 运行成功或 CAPID 初始化。
