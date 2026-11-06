# Sony LDEC / LZ77 格式规格与证据边界

日期：2026-11-02（America/Los_Angeles；公开查询回执为 11-03 UTC）。本目录是独立宿主软件实现，没有 QEMU、runtime 或相机操作。

## 结论与证据等级

**FX3 九份 uxd 的 51,642 条 encoding4/fmt0 资源，全部按下述格式解出精确长度；失败 0，Python/C 字节一致。** 解码输出合计 1,084,897,472 B；39,494 个不同的压缩流/目标长度组合由 Python 和 C 双实现比较，其余重复流仍逐条运行 C 并核对输出 SHA256。

采用以下等级：A1=FX3 原件字节、索引、指令与可重建离线事实；P=固定提交的公开实现佐证；T=宿主代码测试；V=本轮宿主 PNG 目视；U=仍未证实。P、T、V 不代替原 LDEC 硬件或 guest 验收。

| 结论 | 证据 |
|---|---|
| f0/0f 块、LSB 标志、12bit 距离、非线性长度表 | P：Sony 版权 Linux 源码、fwtool、A7C2；A1：全量 FX3 精确解析 |
| 长度表 `3..16,32,64` | A1：870 条小资源构成秩16线性系统，870/870 约束精确；P：Sony `index_to_size` |
| 每个块独立历史、顺序拼接 | P：公开函数以当前输出块为历史起点；A1：293,690 个 FX3 块全部通过当前块距离检查 |
| 本批按4096 B分块，最后一块取剩余长度 | A1：全部51,642条逐块验证，块数等于 ioctl records |
| 宽16像素对齐，LE RGBA4444 | A1：原 libObj 指令、系统格式7描述；V：可辨认图标、橙色选框和面板 |
| 与真实 LDEC 的所有合法/畸形输入行为逐位等价 | **U**：没有硬件输出 oracle，错误和容错策略有意严格 |

完整统计见 [batch_summary.json](results/batch_summary.json)，逐记录源偏移、尺寸、metadata、源/输出 SHA 在 [all_records.jsonl](results/all_records.jsonl)，失败集为 [failures.json](results/failures.json)（空数组）。

## 公开与本地来源

指定的三个本地参考快照经 `rg -i 'uxd|ldec|lz77|lz.?77 decoder'` 均无文本命中；这只证明搜索范围内无匹配，不证明上游无实现。本地 A7C2 摘要没有提到解码器。在线完整 GitHub 树查询（非截断）找到了实际文件；因此没有把搜索引擎无结果当作结论。

1. [Sony 版权 Linux 头文件](https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux/blob/fa5c6f6aba58f675691e5adf291b155b76e6e93e/linux-kernel/include/linux/lz77.h#L62)：固定 `fa5c6f6a`，定义两种块类型、12bit 窗口、最大匹配64及非线性长度表。仓库为公开镜像，不能称为本机 FX3 驱动源码。
2. [Sony 软件 inflate](https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux/blob/fa5c6f6aba58f675691e5adf291b155b76e6e93e/linux-kernel/lib/lz77/lz77_inflate.c#L92) 与 [deflate](https://github.com/DavidBuchanan314/Sony-ILCE-7M4-Linux/blob/fa5c6f6aba58f675691e5adf291b155b76e6e93e/linux-kernel/lib/lz77/lz77_deflate.c)：Sony 2006/2007版权，Dual BSD/GPL 标注，确认标志顺序、终止码、raw长度与正向重叠复制。
3. [ma1co/fwtool.py](https://github.com/ma1co/fwtool.py/blob/cdba742b73eed5981480c326aeb30033aabf0223/fwtool/lz77/__init__.py)：固定 `cdba742b`（提交日期2022-09-14），Python 单块参考，注释指向上面的 Sony kernel 路径。
4. [chocotan/a7c2-qemu C 解码器](https://github.com/chocotan/a7c2-qemu/blob/b3d7c1fed349f1d918acc4259f1d2b3a7c52a500/runtime/analysis/sony-lz77.c)：固定 `b3d7c1fe`（公开 HEAD 查询与既有11月1日摘要一致），独立有界实现与完整块拼接。这里只用其算法佐证；没有搬用 A7C2 的 ioctl、地址、队列或运行配置。

六个文件的 URL、完整提交、内容 SHA256、相关行号及本地搜索范围在 [public_sources.json](results/public_sources.json)。`research_sources.py` 可单独刷新固定 URL 回执，不保存第三方源码；正常 build 不联网。

## 位流规范

源长度和目标长度由外部描述符/ioctl提供；压缩数据不包含图片尺寸或总解压长度。一个源区间是一个或多个连续块，最后一个块结束即必须耗尽源长度。实现不忽略末尾填充字节。

### 压缩块：`f0`

```
f0  flags  token0 ... token7  flags ... END
```

`flags` 从 bit0 到 bit7 消费。每个 bit0 表示一个 literal：复制下一个源字节；bit1 表示两个字节的 codeword `a,b`：

```
length_code = a >> 4
distance    = ((a & 0x0f) << 8) | b
lengths     = [3,4,5,6,7,8,9,10,11,12,13,14,15,16,32,64]
```

distance=0 表示 END，不产生输出；该 flag byte 剩余位不再消费。FX3 全部293,690个 END 都是 `00 00`；公开解码器以 distance=0 判断，长度码任意。参考实现接受任意高nibble的零距离作为 END，此接受域有 P/T 支持，非 FX3 硬件实测。

非零 distance 表示从**当前块已产生的输出**向后 distance 字节，正向复制 `lengths[length_code]` 字节。重叠复制合法：已有 `AB` 后 distance2/length64 会追加 `AB`32次。必须满足 `1 <= distance <= current_block_output_bytes`。不能跨块引用，不使用预置零字典；可表达最大距离4095，FX3本批实见最大4090。

**例：** `f0 0c 41 42 f0 02 00 00` 解出 `AB`33次，共66 B。flag bit0/1为literal，bit2为64字节匹配，bit3为终止。

### 原样块：`0f`

```
0f reserved length_lo length_hi raw_bytes[length]
```

长度是 LE16。reserved 在公开 encoder 中写0、decoder中跳过；本实现不赋予它模式语义。本批 FX3 uxd 没有 raw 块；这条分支只有公开源码与合成测试支持，必须标 P/T，不能称为 FX3 图像实测。

### 块边界与4096 B记录

FX3全量有293,690个压缩块，243,083个完整4096 B块，其余50,607个为最终部分块。没有跨块字典或块间 padding；每条资源的块数精确等于 `ceil(dst_bytes/4096)`，所有非末块恰好4096 B。纯解码API实现一般块语法，没有把4096硬编码成所有Sony流的最大块长度；批量验收另行严格检查FX3硬件记录布局。

压缩源的 DMA 页分段和解压输出的4096 B记录是不同概念；不能在源文件每4096字节强行重置字典。

## 推断与排除过程

[infer_format.py](infer_format.py) 从 `image_02_43.uxc` 的870个目标≤4096 B资源构建每个长度码的出现次数，设未知长度为 L0..L15。每条满足 `literal_count + Σ(code_count[i]*Li) = padded_output_bytes`。高斯消元得秩16、所有方程精确成立，解为上面的非线性长度表；这一步不依赖 numpy、硬件或公开软件运行。

另外筛40个小样本，覆盖起点偏移0..4、LSB/MSB、literal标志极性、字序、高/低nibble长度、长度偏置1..4与距离+0/+1，共1280种 LZSS候选，最佳仅4/40长度吻合。常规LZ10属于该网格；LZ11对skip0/1/4均无完整匹配，标准10/11头匹配0。Sony规则40/40长度通过，附alpha直方图与相邻RGBA相等率。输出统计只是像素合理性指标，不能独立证明真像素。完整可复跑回执为 [format_inference.json](results/format_inference.json)。

## uxd 索引、尺寸和像素域

沿用原审计 `libObj 0x1213fc–0x121500` 索引公式。表记录数为 `u32[t+4]&0x1fff`；基址为 `t+(u8[t]&0x7c)+((u32[t+4]>>11)&0x7ffc)`；短偏移乘4，FFFF缺项。支持原短/长/混合表公式，没有以magic扫描猜记录。

type6资源起点r，q=r+4；encoding=`u32[q]>>28 & 7`、资源格式=`u32[q]>>16 & 0x3f`，宽高=`u16[q+4/q+6]`。无可选属性时长度/相对偏移在q+8/q+12；有bit27时footer=q+12+8*n，n=`u8[q+8]`。源起点为 q+relative。bit31保留，不单独解释为外部文件标志。

本批全部encoding4/格式0：目标字节为 `align_up(width,16) * height * 2`，包含每行 padding。LE16像素为 `R12 G8 B4 A0`，RGBA8各nibble乘17。PNG仅裁掉行padding，raw交付保留padding。不是解压成RGBA8888后再压成4444。

## ldec.ko 施加的约束

本机原件证据入口：[ui-image-resource-load 审计](../../audits/ui-image-resource-load/README.md) 与其 `ui-image-load-proof.json`（本轮SHA=`b476dc75…`）。原libObj SHA=`c4681d20…`；原ldec.ko SHA=`7663d343…`，build每次核验完整SHA。

用户库 VA 为 ELF链接VA，驱动地址为ET_REL `.text+offset`。

| 字段 | 原构造/消费位置 | 约束 |
|---|---|---|
| 源u64虚址 +0、源u32长度 +8 | libObj154db0/154db8；驱动+980/984 | 解析限于源区间，源长度不等于输出长度 |
| 目的u32 p32 +c | 154dc8；驱动+938→arch_p32_to_p64 | 不能套邻机u64物理地址或固定OR高位 |
| 目标u32长度 +10 | 154dd8；驱动+964 | 对齐像素域，cache控制用实际目标长度 |
| records u32 +14 | 154ddc–154de8；驱动+a44→hw_ldec_set | 解码块数，4096 B粒度；非源字节数 |
| DMA通道u32 +18，cache bypass +1c/+1d | 154de0；驱动+92c/+954 | 原调用通道8，源/目的bypass0/1；无token选择位 |

`hw_ldec_set .text+f70–1024`：base+04先写1后写0；+30写7b、+2c写4、+28写7b；+00写0、+0c写records、+10写目的p32（+fdc/+fe8）。这些是原指令值，+00的完整位域含义未恢复，不能给它杜撰LZ10/LZ11切换模式。驱动没有CPU token循环，供数走 `dma330_mem_transfer_async`，完成走IRQ；`.text+da8` 读base+34，状态1返回0，4返回-5，其余返回-13，再唤醒同步wait。

软件解码仅替代字节计算；不能把这些MMIO值直接照搬为宿主内存写，也不发送CP/UIPC/ICDT完成包。真实适配仍须绑定当前位图写锁/活动映射、处理p32转换和生命周期，并在输出可见后返回原同步ioctl。

## PNG 已知明文校验的实际结果

解析image.uxb三组各277个encoding1 PNG，Pillow解出全部831条尺寸正确。其低24bit ID位于另一命名空间，与uxd的ID交集**0**。1531条uxd记录有相同尺寸候选；对PNG做高nibble截取/最邻近4444量化、分别精确RGBA/忽略完全透明像素RGB后，均无完整像素匹配。

所以没有凭相同尺寸绑定身份，没有声称831个PNG是本批的原像素oracle。这项负结果限制了独立像素验收，但不推翻公开规则、全量长度与双实现一致性。样例目视为V级；要提高到硬件逐位等价仍需相同资源的原机/独立可信解码输出。

## 软件接口与保留未证实项

Python `decode_ldec(bytes, exact_size)` 返回新bytes；无效输入抛DecodeError。C `ldec_soft_decode(src,src_len,dst,dst_len,info)` 返回独立enum；dst=NULL可只验证。先验证再写，输入必须保持不可变，源/目标不重叠；失败不改目标。每侧16MiB上限是实现保护，非硬件上限。C没有分配、系统调用、全局可变状态或guest物理地址操作。

本实现对短输入、越界距离、输出过大/过小、未知块与尾随垃圾拒绝；这些返回码不声称复刻硬件畸形流行为。没有原厂错误码映射或取消/并发设备模型。

仍为U：真实硬件逐位oracle、raw在FX3资源中的实际使用、保留位及非规范END的硬件行为、其它encoding/格式、运行高亮/面板具体resource ID身份、guest适配/生命周期/图像写入回执、原菜单高亮修复、实机验收。现有原审计关于AP102 open/errno与失败传播的未证实项也未由离线解码关闭。
