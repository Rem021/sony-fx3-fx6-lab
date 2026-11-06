# FX3 GPE 宿主软件后端核心库

本目录实现独立 C11 库，覆盖活跃 extent/租约、FIFO 批次记录、完成事件，以及受限 FillRect/BitBlit。尚未接入 guest、未修改 runtime、未运行 QEMU 或相机；宿主内存测试通过不代表菜单文字、LCD 显示或真机验收。

## 构建与回执

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-claude/impl/gpe-backend
python3 build_and_test.py
```

退出 0；`build/build.json` 保存完整编译命令、clang 版本、UTC、平台、源文件 SHA256 和编译返回码；`build/test.json` 保存测试返回码、输出、断言数与 sanitizer 状态声明。编译使用 `clang -std=c11 -O1 -g -fsanitize=address,undefined -fno-sanitize-recover=all -fno-omit-frame-pointer -Wall -Wextra -Werror`；测试进程设置 ASan/UBSan halt-on-error，任何构建或测试失败均非零退出，不以旧回执判定成功。

本次工具参数核对了 [Clang ASan 官方说明](https://clang.llvm.org/docs/AddressSanitizer.html) 与 [UBSan 官方说明](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)（2026-11-01 查阅）。协议语义全部来自本地审计原件，网络文档只用于编译检测器用法。

## 证据与实现边界

先完整读取 [公共上下文](../../COMMON-CONTEXT.md)、[GPE 审计说明](../../audits/gpe-menu-draw/README.md)，并完整解析 [proof JSON](../../audits/gpe-menu-draw/gpe-menu-draw-proof.json) 的全部 13,638 条指令记录（每条原指令验证为4B）；JSON SHA256 为 `7be5a7117500a4a9b29104bcc0d1f389a4ed72eef8e4a560f56b73b940012ebd`。关键原代码证据如下，VA 是 libgpe.so 链接地址：

| 依据 | 原地址与指令 | 对应实现 |
|---|---|---|
| FillRect 56B、字段与颜色 | 0xc390–0xc39c 整字 `rev`；0xc400–0xc428 分量高4位；0xc458 selector/alpha 分支；0xc60c–0xc664 坐标/stride | `gpe_plan_fill` |
| BitBlit 144B、快路径分派 | 0xcfa4/0xcfa8 比较目标/源宽高；0xcfb4–0xcfcc flags；0xd010 `bl #0xb234` | `gpe_plan_blit` 的保守支持子集 |
| 快路径完整地址 | 0xb354 `ldp w2,w3,[x19,#0x40]`；0xb35c `madd w0,w3,w0,w2`；0xb37c–0xb3ac 目标修正；0xb364/0xb3b4 读64位基址 | 宽整型地址计算，拒绝溢出，不复现硬件低32位截断 |
| CallbackInfo 24B | 0xaf10 `stp w2,w3,[x29,#0x18]`；0xaf14 `ldp x2,x3,[x4]`；0xaf18 `stp x2,x3,[x29,#0x20]` | `gpe_callback_info`，编译期尺寸断言 |
| 回调16B及先回调后同步回复 | 0xa1a8 清零16B；0xa1b0 序号；0xa1b8 argument；0xa1c0 `blr x1`；0xa1c4–0xa1d4 同步 | `gpe_deliver_one` |
| 同步4B status | 0xa118 `mov x2,#4`；0xa124 `str wzr,[x1,#-4]!`；0xa128 调 SendDrawComp；Main 0x9c34–0x9c4c 失败回复 | status hook 收到4B小端状态 |

参考了 `menu-repair-01/runtime/helpers/fx3-gpe-observe-v12.c` 的 `(gpe,core,sequence,source,param)` worker 风格与五入口，但没有改它。本库没有 gpe/core 路由、符号绑定、`/dev/mem`、DMM 分配事件捕获或 native SendDrawComp 调用；后续 adapter 必须显式提供这些能力。

## 接口与调用约定

接口见 [fx3-gpe-backend.h](fx3-gpe-backend.h)，实现见 [fx3-gpe-backend.c](fx3-gpe-backend.c)。无全局可变状态、无动态分配、无文件/设备/线程操作；context 内有固定容量的表和队列。

1. `gpe_init(ctx,hooks)` 初始化空 context；只可对无在途请求、无外部租约的 context 调用。hooks 在初始化时提供；callback hook 将已验证的64位函数 token 交给可信调用层，不把 guest 数值直接转为宿主函数指针。
2. `gpe_register(ctx,{handle,generation},physical_base,cpu,bytes)` 注册真实映射。64位物理范围与 CPU 映射范围均不可与其他活跃 extent 重叠。所有 handle/generation 非零；同 handle 重注册必须 generation 严格增加。旧 generation 保留墓碑，防止 ABA；最多64个不同 handle，容量不足拒绝，不能覆盖旧墓碑。
3. `gpe_acquire/release` 获取/释放显式租约。租约必须零初始化、不得复制、不得重复释放或覆盖；extent 表由库维护，调用方不得直接改 context 字段。`unregister` 无租约时立即注销；有租约时标记 retiring 并返回 BUSY，此时不得释放 CPU 存储。新 acquire/绘制拒绝 retiring；最后一个租约释放后自动注销。CPU 指针必须由调用者保证真实可访问且至少 bytes 大，库无法证明宿主指针背后的映射真实性。
4. `gpe_begin_batch(ctx,id)` 开始显式 FIFO 批次，id 不可重复；只有上一批事件全部交付后可开始下一批。最多64个批次记录，满则拒绝；当前版本没有在线回收 API，长期集成须在静止点导出回执并有序重建 context。
5. `gpe_plan_fill/blit(raw,n,plan)` 为纯解码/规划函数，只校验参数及数学范围；不解析 extent、不写像素。调用者保证 raw 可读 n 字节且 plan 为有效、不与 raw 重叠的输出对象。
6. `gpe_submit(ctx,opcode,sequence,source,raw,n,dst_ref,src_ref)` 接收参数体（不含16B FIFO头），长度必须精确。refs 来自真实分配层的当前 handle/generation；地址可以位于 extent 内的 payload 偏移。每个源/目标整行逐行预检，全部通过后才写第一像素；不能将跨两个相邻 extent 的矩形拼成合法 surface。按行写入保留 padding。完成队列满时也在写入前拒绝。
7. `gpe_deliver_one` 每次消费一个事件；EMPTY 表示无事件。成功请求 callback 非零则入24B CallbackInfo，调用 hook 时编码16B `{u32 sequence,u32 zero,u64 argument}`；async=0 在回调后向 source 交付4B status，async非零且 callback=0 无完成事件。事件持有源/目标租约至交付结束，保证 callback 观察到的像素写入先于交付。失败绘制不会调用成功回调；能解码完成字段的同步失败会入队非零状态。

状态码为本库 `gpe_status`，**不是 Sony 原生数值 ABI**；后续 adapter 须明确映射，不可直接宣称原生错误码等价。同步 source=0 是 INVALID。未知 opcode/错误长度因无法安全解码 completion 字段，仅返回错误并记批次，不自动回复；队列满同样由 submit 返回 CAPACITY，adapter 必须按 Main 的失败路径处理，不能吞错或返回成功。所有错误均不写任何像素（DELIVERY 是已经完成写入后的交付错误，不能当成像素回滚）。

完成事件在调用 hooks 前已出队，hooks 失败返回 DELIVERY 并增加 `delivery_failures`，不自动重试，避免重复调用；callback 调用失败时后续同步状态也改为 DELIVERY。它提供顺序、单次**尝试**，不承诺外部 transport 的 exactly-once 成功。需要可靠重试时应在可信消息层添加可证明的交付协议。

批次记录保留 commands、failures、first_error、first_sequence、delivery_failures；Flush 报本批 first_error，无错误时允许空批同步 Flush。失败 Flush 自身也计入 failures。下一批错误状态重新开始，旧批记录保留；不会使用 v12 永久 `raster_failed` 锁死全部后续请求。先前成功命令不因稍后命令失败回滚，零写入保证以单条失败绘制命令为边界。

## 像素支持范围

FillRect 只支持 format0/1、selector0、alpha255。format0 的数值为 `(c0>>4)<<12 | (c1>>4)<<8 | (c2>>4)<<4 | c3>>4`，以小端2B存放；format1 数值为 `c0<<24|c1<<16|c2<<8|c3`，以小端4B存放。颜色名不武断指定 RGBA 上层语义。

BitBlit 只支持相同 format0/1、目标/源宽高相等、rotation=0、selector=0、转换mode=0、alpha255、0x73..0x78 flags全部0；scale字段只接受0或浮点1的原位模式（原快路径忽略这两个槽，额外限制用于保守准入）。源/目标 stride 各自计算：

```
src = u64@38 + bpp * (P44 * P58 + P40)
dst = u64@00 + bpp * ((P0c + P2c - P54) * P30 + P08 + P28 - P50)
width = P48; height = P4c
```

坐标项先按有符号32位扩展再用64位运算；负坐标、零宽高、超 stride、非法 clip、地址溢出拒绝。每行最大受 extent 大小约束，行数最多65,536以限制预检资源消耗。

**clip 是保守范围门禁**：要求目标完整矩形位于非负、非空的 P18/P1c/P20/P24 内；不对部分越出 clip 的图元自行裁剪。原0xb234未编程通用路径0xbc88的 clip 寄存器，部分裁剪方向/坐标语义未闭合。任意源/目标物理包络重叠拒绝 OVERLAP，连仅 padding 包络相交也保守拒绝；注册时也拒绝 CPU alias。因此不猜测 memmove 方向。

alpha混合、格式转换、format2/3/4及未知格式、opcode2/3、特殊 flags、缩放旋转显式 UNSUPPORTED；边界/clip/退役请求使用各自错误码。padding、未消费颜色槽不会被解释为新的 flags。

## 线程与内存安全约定

同一 context 的**全部调用必须由调用方同一把外部互斥锁串行化**，包括 allocation/unregister、lease、begin、submit、deliver 和状态读取；库无内部锁，不可并发使用相同 context。不同 context 仅在映射内存互不相交且生命周期独立时可并行。持锁调用 hooks，hooks 不得重入同一 context、改写其结构或解锁/释放映射；主要公开可变 API 对 delivering 状态返回 BUSY。调用者必须保证输入参数在调用期间稳定、CPU 映射在租约期间有效，禁止 DMA/其他线程同时修改像素。

C11 release/acquire fence 标明 CPU 写入→完成交付顺序；外部互斥锁负责跨线程同步。本库 fence 不代表设备 cache flush、DMA 可见性、硬件中断或 LCD 提交。租约用于防止释放，不是相机 DMM pin/unpin 实证；只有真实 allocation owner 尊重 BUSY 和生命周期合同后才可接 guest。

## 测试矩阵与未证实项

| 测试组 | 可观察检查 |
|---|---|
| pixels | format0/1 不同通道、逐通道颜色、非零x/y、stride、整缓冲区比对确认行 padding 未触碰 |
| rejects | 第一行合法但后行越界零写入、相邻extent边界、注销/retiring、旧generation、重复release、alias拒绝、负坐标、64位溢出、零宽、未知格式、blend、alpha、opcode2/3、错误长度 |
| copies | 两格式非零图案跨行复制、不同stride、目标加减修正公式、全缓冲区比对、重叠零写入、clip门禁、所有6个 flags、转换/旋转/缩放拒绝、源/目标范围预检 |
| completions | 同步4B0、失败非零、24B队列与16B参数、FIFO callback→status、仅async callback、延迟至交付释放租约、单次/EMPTY、空批Flush、失败批次与下一批恢复、hook失败、重入拒绝 |
| capacity | 128个事件饱和时第129个请求零写入、全部交付后租约归零 |

仍未证实：真实菜单命中本支持子集的频度、AP 字形bitmap绑定、部分 clip 语义、重叠复制方向、alpha数学/舍入/预乘、格式2/3/4、CLUT是否存在、LTT/UX资源解码、真实DMM事件与generation绑定、native status映射、可靠外部完成传输、LCD提交和设备显示。以上不由宿主回执补齐。
