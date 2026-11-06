# LDEC LZ77 软件解码器（独立宿主交付）

**格式已恢复，51,642/51,642条解压长度精确匹配，失败0，Python/C一致。** 原始资源只读，所有代码、测试、回执与样例均在本目录；未启动QEMU、未改runtime或固件。

- [格式规格、原代码地址与未证实项](lz77_format.md)
- [全量统计](results/batch_summary.json) · [逐记录偏移/metadata/源与输出SHA256](results/all_records.jsonl) · [失败样本](results/failures.json)
- [样例总览 PNG](samples/contact-sheet.png) · [橙色高亮填充](samples/highlight-fill-01-1356.png) · [橙色高亮边框](samples/highlight-frame-01-1533.png) · [面板](samples/panel-02-1228.png)
- [公开原始来源的URL、固定提交与内容SHA](results/public_sources.json) · [候选格式筛选与长度表推断](results/format_inference.json)
- [构建/测试日志](results/build_and_test.log) · [编译器及源哈希回执](results/build_receipt.json)

## 复跑

在本目录运行（macOS）即可重新编译并生成全部回执和样例：

```sh
python3 -B build_and_test.py
```

需要系统Python3、clang及已安装的Pillow；Pillow仅用于831个PNG的比较及样例总览，核心解码器只依赖Python标准库。正常build不联网，会在写入前检查外盘UUID；从固定绝对路径只读九份uxd、image.uxb及既有审计，核对原件完整SHA。

输出包括宿主dylib、AArch64 freestanding `.o`、ASan/UBSan独立测试程序、单元/变异测试、全量JSONL和PNG。AArch64对象仅编译成功，未链接guest内核或执行。

```sh
# 可选：只读刷新固定公开源码的元数据回执，不保存第三方源码
python3 -B research_sources.py

# 纯Python单独解出已交付的320x52高亮（输出大小含行padding）
python3 -B decode_ldec.py samples/highlight-fill-01-1356.ldec samples/highlight-check.png \
  --size 33280 --width 320 --height 52
```

## 结果与接口

全部输出合计1,084,897,472 B；51,642条均由C解码，39,494种不同源流/长度由Python逐字节交叉验证，重复流核对源/输出SHA。293,690个块全部为f0压缩块；非末块4096 B，块数与原ioctl的records匹配。最大实见距离4090。每个样例同时保留 `.ldec` 压缩流与含行padding的 `.raw` 输出。

Python入口：`decode_ldec(source, exact_output_size) -> bytes`；`decode_details`另返回块和token统计。C入口：`ldec_soft_decode(src, src_len, dst, dst_len, info)`；返回0为成功，非0为本实现错误，`dst=NULL`可只验证。C先完整验证再写，输入需要在两遍中保持不可变；失败不覆盖目标，源/目标不得重叠。API没有设备/物理地址/系统调用，适合后续包装，但本轮没有适配guest。

已测试所有16个长度码、重叠复制、标志位顺序、多块/字典重置、最大4095距离、raw分支、真实小流、缺失终止/短输入/错误长度/尾随垃圾、200组合成编码以及3000次确定性变异。C独立程序在ASan/UBSan下验证越界拒绝、失败不写和重叠拒绝。

## 样例解释与验收边界

PNG使用LE16的R12/G8/B4/A0，每nibble乘17，裁掉行padding；总览合成在棋盘格上显示透明部分。可辨认3D、S&Q和222M等图标，320x52橙色填充/边框可作为高亮九宫格候选，640x384可作为面板候选。候选由原记录尺寸/metadata及图像内容识别，**没有绑定AP102运行时的具体bitmap/resource ID**。

831个内嵌PNG与uxd无相同ID；1531条尺寸候选在两种4444量化和透明RGB归一化下都无完整像素匹配，因此未取得PNG已知明文oracle。不能把双实现一致、长度100%或样例可读称为硬件逐位等价。

后续仍需由Lead实现真实源/目标租约与p32映射、解码后写入和原同步完成，并在guest捕获同一资源身份的输出、GPE源与菜单画面。raw在FX3图像中的使用、硬件畸形流行为、其它格式/encoding、真实菜单修复与实机验收仍未证实。原审计关于AP102实际open/errno的缺口也保留。

公开规则来自Sony版权Linux代码的固定镜像、ma1co/fwtool以及chocotan/A7C2；详见[规格来源](lz77_format.md)与[来源许可说明](NOTICE.txt)。没有保留第三方源码副本。
