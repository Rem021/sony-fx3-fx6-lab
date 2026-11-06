# AP104 既有日志性能分解

Same-worker consecutive original adapter return timestamps provide wall-time envelopes; NOT command CPU/sole backend duration. All enqueue/start/backend clocks, life-lock waits and FIFO depth absent are null. Envelopes include producer/dequeue gaps, scheduling/QEMU pauses, validation/mmap, rendering, copies, hashes and text output.

失败序1207，QID 0x808261c0；last successful Flush返回至失败Flush返回 61.569433s；领取到释放 5.285999s；释放返回至首次零完成投递 44.711702s。

逐条表：[ap104-light1200-performance-v3.csv](ap104-light1200-performance-v3.csv)；完整字段/原行号：[ap104-light1200-performance-v3.json](ap104-light1200-performance-v3.json)。入队、开始、backend分段、life锁等待和worker深度全部未记录，表中留空，不用终点间隔冒充这些值。

|路径|命令数|整批终点间隔(s)|释放后至首投递窗口占比(s)|纹理观察复制/三SHA字节|
|---|---:|---:|---:|---:|
|blit|Kblend:255|70|25.218467|21.971897|1851414|
|blit|stretch:nearest_v1|Kblend:255|44|20.533482|18.792854|1421640|
|blit|fmt2|Kblend:255|18|5.074471|3.917563|0|
|flush|1|0.085616|0.029388|0|
|fill|replace|1|9.679061|0.000000|0|
|fill|Kblend:255|3|0.159848|0.000000|0|
|blit|fmt2|Kblend:128|6|0.281195|0.000000|0|
|blit|Kblend:65|6|0.357364|0.000000|0|
|blit|tile|Kblend:255|3|0.130597|0.000000|11376|
|fill|Kblend:216|1|0.049332|0.000000|0|

## 最大终点间隔（非实测backend耗时）

|seq|op|src/dst fmt|raw dst尺寸|path|终点间隔(s)|释放后窗口交集(s)|
|---:|---|---|---|---|---:|---:|
|1055|FillRect|0/0|640×480|fill|replace|9.679061|0.000000|
|1165|BitBlit|0/0|16×2|blit|Kblend:255|4.747750|4.747750|
|1159|BitBlit|0/0|441×2|blit|stretch:nearest_v1|Kblend:255|3.954488|3.954488|
|1161|BitBlit|0/0|40×40|blit|Kblend:255|2.925427|2.925427|
|1162|BitBlit|2/0|219×42|blit|fmt2|Kblend:255|2.181211|2.181211|
|1174|BitBlit|0/0|6×37|blit|stretch:nearest_v1|Kblend:255|2.095483|2.095483|
|1160|BitBlit|0/0|16×2|blit|Kblend:255|2.084650|2.084650|
|1177|BitBlit|0/0|6×6|blit|Kblend:255|1.945777|1.945777|
|1169|BitBlit|0/0|441×2|blit|stretch:nearest_v1|Kblend:255|1.533377|1.533377|
|1175|BitBlit|0/0|461×37|blit|stretch:nearest_v1|Kblend:255|1.517729|1.517729|
|1164|BitBlit|0/0|441×2|blit|stretch:nearest_v1|Kblend:255|1.458339|1.458339|
|1154|BitBlit|0/0|441×2|blit|stretch:nearest_v1|Kblend:255|1.302799|1.302799|
|1163|BitBlit|0/0|16×2|blit|Kblend:255|1.277258|1.277258|
|1176|BitBlit|0/0|6×37|blit|stretch:nearest_v1|Kblend:255|1.274290|1.274290|
|1153|BitBlit|0/0|16×2|blit|Kblend:255|1.268497|0.932303|
|1178|BitBlit|0/0|461×6|blit|stretch:nearest_v1|Kblend:255|1.190632|1.190632|
|1158|BitBlit|0/0|16×2|blit|Kblend:255|1.128949|1.128949|
|1183|BitBlit|0/0|5×50|blit|stretch:nearest_v1|Kblend:255|0.914124|0.914124|
|1168|BitBlit|0/0|16×2|blit|Kblend:255|0.879011|0.879011|
|1167|BitBlit|2/0|49×42|blit|fmt2|Kblend:255|0.871492|0.871492|

仅有显式command-lock竞争marker可计时；本批其他命令无marker不等于所有锁等待为零。命令返回标记位于tex102_emit之后，纹理复制/SHA/直方图和串口日志均包含在终点间隔；源代码表明这些工作可能占成本，但现有时钟不足以把其耗时与backend像素循环分离。历史v24轮无该逐命令ns，不能把printk时钟拼接成用户态命令耗时。
