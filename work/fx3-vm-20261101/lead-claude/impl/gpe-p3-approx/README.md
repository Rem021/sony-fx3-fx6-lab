# GPE P3 近似混合：backend v2 / guest adapter v14

2026-11-02。`python3 build_and_test.py` 退出0，生成 aarch64 `fx3-gpe-observe-v14.so`，原 v13 测试与新增 ASan/UBSan 测试全部通过。**这是近似视觉模型，非逐位原厂等价；没有 guest/QEMU、菜单、LCD 或实机验收。** 仅写本目录，未修改原 `impl/gpe-backend/`、`impl/gpe-adapter-v13/`、runtime、STATE、候选CPIO，未启动QEMU。

当前共享库 SHA256：`836b78c4a290ece86d27d1e2a5d99097be570974ef2acdeee9a3c4314d6a41bb`。SONAME 为 `fx3-gpe-observe-v14.so`。以每次 [构建回执](fx3-gpe-observe-v14-build.json) 的 `output_sha256` 为准。

## 复核与交付入口

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-claude/impl/gpe-p3-approx
python3 build_and_test.py
```

- [fx3-gpe-backend-v2.c](fx3-gpe-backend-v2.c)、[头文件](fx3-gpe-backend-v2.h)：由 v1 复制扩展，保留 gpe_* API 名称，plan 增加近似混合、K、H/V字段。无文件、设备、动态分配或线程操作，调用者仍须串行化同一context。
- [fx3-gpe-observe-v14.c](fx3-gpe-observe-v14.c)、[共享库](fx3-gpe-observe-v14.so)：完整guest拦截库；[adapter.inc](adapter.inc) 为其适配段，[make_source.py](make_source.py) 从本地冻结v13重建，`--check`只读比对。
- [reference-v13/](reference-v13/)：原 v13 C/后端/测试的原样冻结副本；[check-adapter-v13-regression.c](check-adapter-v13-regression.c) 仅把include改为v14，其余断言不变。
- [check-approx-backend.c](check-approx-backend.c)、[check-approx-adapter.c](check-approx-adapter.c)：新增像素、安全边界、完成与marker测试；[make_vectors.py](make_vectors.py) 用Python Fraction独立计算期望，输出 [expected-vectors.json](expected-vectors.json) 及C常量表。
- [build/test.json](build/test.json)：每次真实编译与运行的命令、退出码、stdout/stderr、源文件SHA256、ELF/SONAME/依赖核验；`build/*.log` 为四套完整宿主回执。
- [provenance.json](provenance.json)：本次阅读时公共上下文、Lead计划、审计及原实现输入哈希；[proof-readback.json](proof-readback.json) 为完整proof解析及记录检查摘要。原审计proof SHA256 为 `51c1b7c6752910b132d929851330844ab0e53e2da9ebf0df1ab03047685cd51e`。

构建沿用v12/v13的Zig工具与guest libc/libdl/libpthread/loader：`aarch64-linux-gnu.2.25 -nostdlib -shared -fPIC -O2 -mno-outline-atomics -Wl,--no-undefined`。完整参数在 [cross-args.json](cross-args.json)；只替换v14输入/输出、SONAME、本目录compat与v2后端。Zig global/local cache均在本目录 `zig-cache/`，TMPDIR在 `build/`。构建脚本写入前核验目标卷UUID。

## 公式、精度与假设

本任务遵循 [PLAN.md 的2026-11-02 GPE P3 Lead决策](../../PLAN.md) 及派发的显式公式，覆盖审计不能逐位闭合的混合分支。审计 [README](../../audits/gpe-blend-p3/README.md) / [proof](../../audits/gpe-blend-p3/gpe-blend-proof.json) 的硬件算术门禁仍成立；本次开放的是明确标记的近似模型。

令所有通道为0..255整数，`As`、`Ad` 为源/目标c3，`K`保留原8bit值。`R255(n)=floor((n+127)/255)`：

```text
a8 = R255(As * K)
Co8 = R255(Cs * a8 + Cd * (255 - a8))  // c0,c1,c2各自计算
Ao8 = a8 + R255(Ad * (255 - a8))
```

即归一化记法 `a=As*K/255`、`Co=Cs*a+Cd*(1-a)`、`Ao=a+Ad*(1-a)`，中间a先量化到8bit。所有乘加用足够宽的unsigned整数，不进行gamma/线性光转换、dither或额外tint。输入RGB允许大于As；As=0保留目标全部通道，避免透明边缘的非零RGB泄漏。

**舍入是假设**：每次除255均四舍五入；fmt0结果每分量用 `floor((Co8+8)/17)`、alpha同式四舍五入至0..15，再按c0..c3从高到低打包为LE16。fmt0原始Fill输入仍先使用审计的高4bit截断 `c>>4`；源/目标已打包的4bit分量再用 `nibble*17` 扩展为8bit。fmt1保持数值 `c0<<24|c1<<16|c2<<8|c3`、LE32存储。**原fmt0覆写路径保持高4bit截断，未改为四舍五入。**

Fill selector1与selector2在本模型中都使用上述公式，虽然原寄存器分别为`05040501`与`0c000100`、selector2的B05低字节恒零。BitBlit selector0/K<255与selector1任意K也统一采用上述近似式；并未把`09080901`译为已证实的alpha因子。selector0/K255仍保持复制/覆写，不因源alpha非满而混合。

模型名称为 `straight_over_v1`，含义以本节公式为准：按任务约定，RGB的Cd项不再乘Ad，也不除以Ao归一化；Ad只参与输出alpha。通用透明目标上不能据名称宣称完整Porter–Duff straight-storage等价。[W3C compositing 2024-03-21规范](https://www.w3.org/TR/compositing-1/#simplealphacompositing) 的公式区分straight输入与premultiplied输出，目的仅为核对术语，不是Sony硬件oracle；本次不改变Lead给定公式。

## 准入表

下表为本软件子集，不代表原厂合法组合的全集。所有成功路径仍要求当前extent、逐行完整span、完整clip门禁、无源/目标物理包络重叠；跨fmt、部分clip、缩放/旋转均未开放。

| 命令/字段 | 准入行为 | 标记/依据 |
|---|---|---|
| Fill fmt0/1，selector0，K255 | 原精确pack覆写 | `approx_blend=0 formula=none`；原`0xc390/0xc400/0xc50c` |
| Fill fmt0/1，selector1/2，K0..255 | 本节近似混合 | `approx_blend=1 formula=straight_over_v1`；原`0xc520..0xc5dc`描述符+Lead显式覆盖 |
| Fill selector0，K<255 | unsupported，零像素写入 | 本派发仅开放Fill selector1/2；常量插值因子仍未闭合 |
| Fill其他selector或fmt2/3/4/未知fmt | unsupported | 不复现assert、不补造成功 |
| BitBlit src=dst fmt0/1，selector0，K255 | 原按行复制；可附H/V翻转 | 无混合；原`0xb578`关闭混合 |
| BitBlit同fmt0/1，selector0/K<255或selector1/任意K | 本节近似混合；可附H/V翻转 | `approx_blend=1 formula=straight_over_v1` |
| BitBlit flags@0x73..0x76 | 必须全0（高nibble也检查） | 未知通用运算/采样保持拒绝 |
| BitBlit H@0x77、V@0x78 | 各仅0或1；1翻转请求源矩形内像素 | 原`0x13e34..0x13e58`；2..255仍保守拒绝 |
| BitBlit转换mode@0x71 | 仅0 | 沿用v13保守门禁；即使fmt0/1原路径不消费该槽，也未扩大准入 |
| BitBlit selector2、3..255 | unsupported | selector2原错误`0xcf48..0xcf88`；其他非零别名不充新ABI |
| BitBlit跨fmt、fmt2/3/4、rotation非0、源/目标尺寸不同 | unsupported | mode1..4矩阵、CLUT/颜色空间、采样均未开放 |
| scale@0x60/@0x64 | 仅0或float1原位`0x3f800000` | 沿用v13额外保守门禁 |
| Flush | 沿用v13已有成功draw且无粘滞失败；padding1..7全0 | async/callback/argument语义不变 |
| opcode2/3、其他opcode | 后端unsupported | 不在本次扩展内 |

H/V基于源crop后的请求宽高，H翻转 `sx=w-1-x`，V翻转 `sy=h-1-y`，不反转padding或整幅extent。无flags快路径不读取BitBlit颜色@0x6c..0x6f；仅H/V通用子集中本模型也不把该色当tint，f75/f76保持0。该通用子集的像素等价性仍属近似、未经过芯片oracle。

## 与v13差异和保留语义

只改变后端规划/raster扩展、adapter版本/后端include和marker段。`make_source.py --check`证明其余绑定/截获代码来自冻结v13：五个入口、符号/GOT/16B原指令校验、setup `0xdb74`、Application_System_Init trampoline、BT error透传、原GetInstance/Main/FIFO都保留。

固定545 extent仍为base `0x43feb5000`、bytes `0x140000`，可写payload从 `0x43feb5100` 到 `0x43fff5000`（尾端不含）；前0x100B头禁止绘制。所有源/目标行须完整在payload内；命令前/中/后沿用 `/proc/udm/dmm_extents` 检查，不调用GetDmmMemInfo，不扩大地址准入。generation1仍是命令局部标签，不是实证分配代次。

每命令仍初始化后端context、只注册545、执行副本置async并清完成字段；CPU写入、屏障、extent后验、munmap以后才callback。callback参数仍为16B `{u32 sequence,u32 zero,u64 argument}`，callback先于同步4B0；async无callback无完成，source0不发同步回复。所有错误返回5，仅由原Main发送非零失败状态，adapter不重复发失败。内联callback时机与原原生CallbackFifo等价性、真正DMM pin/unpin仍未证实。

事前准入/边界/clip/重叠拒绝保证零像素写入；extent后验、munmap或transport失败可能发生在写入之后，沿用v13返回5并锁住Flush，不承诺回滚。

## Marker合同

保留v13全部原字段与按op统计，新增 `approx_blend=0|1 formula=none|straight_over_v1 selector= K= rotation= src_fmt=`。`flags`旧编码不变：Fill为selector<<8|K；BitBlit为六flags低48bit、selector占48..55、conversion占56..63。源/目标地址仍为原始完整64bit基址，不是修正首像素。

前200条命令逐条输出；之后非混合成功命令沿用2的幂统计。**每条混合请求和每条失败请求无论计数多少均输出FX3_GPE_CMD**，混合请求包含指定近似标记；候选混合被拒绝时仍标明请求选择的模型，result5表示没有成功完成，不能由approx_blend=1推断已写像素。

每个拒绝另输出 `FX3_GPE_REJECT_PARAMS op= seq= read= len= raw_hex=`，read1时为完整56/144/24B参数小写hex，无截断、无200条抑制，包含全部地址、stride、clip、mode、flags和callback。无法完整读取时read0/len0/raw_hex=unavailable，不把零填充数组伪装成实读参数。BUSY路径同样完整记录已读参数。原始参数记录仅在本地guest日志使用。

## 验证回执与剩余边界

| 宿主测试 | 结果 |
|---|---|
| 冻结原v13+原后端+原测试 | 全部原断言通过 |
| v14+v2运行同一v13测试（只换include） | 全部原断言通过，包括1100命令的200明细+3汇总 |
| v2像素与安全矩阵 | 250组独立有理数期望；500 Fill、2000 BitBlit；4094次拒绝零写入；22306检查 |
| v14适配器新增矩阵 | 混合callback→同步、Flush、fmt0/1翻转、边界/格式/mode拒绝、完整参数日志、超过200后每条混合标记；279条混合marker、15条完整拒绝记录，其中1条读取不可用 |

输入As/K/Ad覆盖0、1、127、254、255；fmt0明确区分原输入高bit截断与中间8bit精度。透明源带非零RGB、透明/半透明目标、各H/V组合、crop/修正坐标、不同stride和padding均覆盖。flags全u8枚举，含高nibble和翻转2..255；跨fmt、format2..4、旋转/缩放、部分clip、源/目标后行越界、重叠全部零写入。

宿主使用 `-fsanitize=address,undefined -fno-sanitize-recover=all -Wall -Wextra -Werror`；ASan/UBSan halt-on-error，macOS关闭不支持的LeakSanitizer，四套无诊断。构建通过只证明本选定模型及宿主安全/完成测试，不证明真实纹理均未预乘、硬件精度/采样/混合因子、动态extent生命周期、guest绑定/callback调度、LCD或可操作菜单。

## 给运行链持有者的集成步骤（本工人未执行）

1. 在本目录重跑 `python3 build_and_test.py`，核对最新SHA256、ELF aarch64与SONAME；只读取已有runtime工具链/SDK，不覆盖v12/v13原件。
2. 在**新的候选CPIO**内，用本目录v14 `.so`替换成员 **`simulation/fx3-gpe-observe-v7.so`** 内容。该成员名是v13沿用的启动合同；保持一个版本，不同时preload v13/v14。
3. 保留 `LD_PRELOAD` 的 `/simulation/fx3-gpe-observe-v7.so` 位置、其他库顺序及 `LD_LIBRARY_PATH=/simulation:/usr/lib:/lib`；没有新增环境开关。权限仍需 `/proc/self/mem`、`/proc/udm/dmm_extents`、callback时 `/proc/self/maps` 与读写 `/dev/mem`。
4. 由Lead持有运行链锁、按既有方法更新CPIO/DTB/哈希/STATE并启动；检查 `FX3_GPE_BOUND ... adapter=v14 approx_model=straight_over_v1` 和每条混合命令的 `approx_blend=1 formula=straight_over_v1`。
5. 按真实请求统计准入与拒绝，独立物理面readback核对像素，再核对完成无重复、等待者退出及最终显示提交。未知地址/格式/flags依旧拒绝并按完整参数重新审计；新后端输出不能作为原厂硬件oracle。
