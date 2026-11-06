# AP104 既有日志性能分解

Same-worker consecutive original adapter return timestamps provide wall-time envelopes; NOT command CPU/sole backend duration. All enqueue/start/backend clocks, life-lock waits and FIFO depth absent are null. Envelopes include producer/dequeue gaps, scheduling/QEMU pauses, validation/mmap, rendering, copies, hashes and text output.

失败序1207，QID 0x808261c0；last successful Flush返回至失败Flush返回 61.569433s；领取到释放 5.285999s；释放返回至首次零完成投递 44.711702s。

逐条表：[ap104-light1200-performance-v2.csv](ap104-light1200-performance-v2.csv)；完整字段/原行号：[ap104-light1200-performance-v2.json](ap104-light1200-performance-v2.json)。入队、开始、backend分段、life锁等待和worker深度全部未记录，表中留空，不用终点间隔冒充这些值。

|路径|命令数|整批终点间隔(s)|释放后至首投递窗口占比(s)|纹理观察复制/三SHA字节|
|---|---:|---:|---:|---:|
|fill|replace|1|0.000000|0.000000|0|
|fill|Kblend:255|3|0.000000|0.000000|0|
|blit|fmt2|Kblend:255|18|0.000000|0.000000|0|
|blit|Kblend:255|70|0.000000|0.000000|1851414|
|blit|fmt2|Kblend:128|6|0.000000|0.000000|0|
|blit|Kblend:65|6|0.000000|0.000000|0|
|blit|tile|Kblend:255|3|0.000000|0.000000|11376|
|blit|stretch:nearest_v1|Kblend:255|44|0.000000|0.000000|1421640|
|fill|Kblend:216|1|0.000000|0.000000|0|
|flush|1|0.000000|0.000000|0|

## 最大终点间隔（非实测backend耗时）

|seq|op|src/dst fmt|raw dst尺寸|path|终点间隔(s)|释放后窗口交集(s)|
|---:|---|---|---|---|---:|---:|
|1055|FillRect|0/0|640×480|fill|replace|-338.588159|0.000000|
|1056|FillRect|0/0|640×56|fill|Kblend:255|-348.267220|0.000000|
|1057|FillRect|0/0|640×46|fill|Kblend:255|-348.311436|0.000000|
|1058|FillRect|0/0|640×384|fill|Kblend:255|-348.351433|0.000000|
|1059|BitBlit|2/0|139×38|blit|fmt2|Kblend:255|-348.427068|0.000000|
|1060|BitBlit|0/0|27×27|blit|Kblend:255|-348.469074|0.000000|
|1061|BitBlit|2/0|227×38|blit|fmt2|Kblend:128|-348.524400|0.000000|
|1062|BitBlit|0/0|27×27|blit|Kblend:65|-348.568139|0.000000|
|1063|BitBlit|2/0|231×38|blit|fmt2|Kblend:128|-348.650478|0.000000|
|1064|BitBlit|0/0|27×27|blit|Kblend:65|-348.695673|0.000000|
|1065|BitBlit|2/0|222×38|blit|fmt2|Kblend:128|-348.744768|0.000000|
|1066|BitBlit|0/0|27×27|blit|Kblend:65|-348.797944|0.000000|
|1067|BitBlit|2/0|210×38|blit|fmt2|Kblend:128|-348.843742|0.000000|
|1068|BitBlit|0/0|27×27|blit|Kblend:65|-348.890414|0.000000|
|1069|BitBlit|2/0|105×38|blit|fmt2|Kblend:128|-348.964430|0.000000|
|1070|BitBlit|0/0|27×27|blit|Kblend:65|-349.015950|0.000000|
|1071|BitBlit|2/0|202×38|blit|fmt2|Kblend:128|-349.066851|0.000000|
|1072|BitBlit|0/0|27×27|blit|Kblend:65|-349.107744|0.000000|
|1073|BitBlit|0/0|20×378|blit|Kblend:255|-349.162959|0.000000|
|1074|BitBlit|0/0|640×384|blit|Kblend:255|-349.217113|0.000000|

仅有显式command-lock竞争marker可计时；本批其他命令无marker不等于所有锁等待为零。命令返回标记位于tex102_emit之后，纹理复制/SHA/直方图和串口日志均包含在终点间隔；源代码表明这些工作可能占成本，但现有时钟不足以把其耗时与backend像素循环分离。历史v24轮无该逐命令ns，不能把printk时钟拼接成用户态命令耗时。
