# FX3：START/STOP回复类型与MAIN消息发布

本轮把上一阶段仅称为type3的消息，绑定到原跳转表与日志名称：**type0是`IMOLA_ENC_START_DONE`，type3是`IMOLA_ENC_STOP_DONE`。** 上一阶段的四类参数归还路径因此明确对应STOP_DONE消费，不能当作START_DONE的参数释放入口。

正式运行通过133段原片段、9次客体原型调用，包含15种原回复类型、25个stream谓词输入和9组发布对照。真实底层传输、消息与当前请求/配置代次关联仍未绑定；没有相机或硬件接受、录制和恢复验收。

## 类型名称与原始字节的绑定

原0x22873c从消息+2取类型，读取原0x37be00的15项跳转表，再选择对应日志字符串。本轮执行每个原分派前缀，在实际诊断入口前停止，并静态核对后面的原字符串引用。没有伪造日志返回值。

| 类型 | 原名称 |
|---:|---|
| 0 | IMOLA_ENC_START_DONE |
| 1 | IMOLA_FMCRX_DONE |
| 2 | IMOLA_ENC_BSO_DONE |
| 3 | IMOLA_ENC_STOP_DONE |
| 13 | IMOLA_ENC_CHANGE_PARAM_DONE |
| 14 | IMOLA_INIT_DONE |

其余原解码回复名称保存在完整结果中。这里绑定的是本文件中这些消息值的含义，不能由名字推出事件到达时硬件一定正常、所有消费者已退出或机身恢复完成。

## MAIN与可选回调的边界

原0x2280c0的接收包装路径按消息中的通道字节查找owner，从空闲池借消息缓冲，之后执行必经诊断。本轮在诊断前停止，再用捕获的寄存器、栈帧和缓冲作为独立后续片段输入；没有执行完整接收函数。

后续调用原0x226ad4/0x27cf58，读取owner+0xe128。对0–24的原执行结果，**仅22和23返回真，MAIN HEVC_MP4的14返回假**。因此当前MAIN输入即使提供非空START/STOP可选回调指针，也不会调用它们，而会将消息加入owner待处理队列。

另用显式非目标stream22输入执行回调分支，在原START/STOP调用入口前停止。该分支的调用点位于待处理队列发布之前；回调本身未执行。这个对照只检查分派条件与顺序，不是stream22编码有效性或16M MAIN模式。

原文件里能找到still-encode类的`enc_start_done`回调类型名。它与上述谓词边界一致，不能因为名字相似便接到MAIN完成协议上。

## 原RTTI执行与消息发布

独立后续片段实际执行了原C++类型转换帮助函数0x1a58及其原单继承RTTI遍历，使用原`imola_common_api_enc_handler`与`imola_common_enc_dec_base_handler`元数据。owner虚表和注册树是显式fixture；没有把类型转换输出替换成预设成功值。

RTTI结构解释参考[Itanium C++ ABI](https://itanium-cxx-abi.github.io/cxx-abi/abi.html#rtti-layout)，实际地址、布局和执行仍以本固件字节为证。该通用说明不是Sony模块ABI、真实对象构造或运行时地址映射的保证。

MAIN正例在原复制后通过0x22c574发布消息：待处理计数从0变1，队列项记录原类型及消息缓冲地址。此时四个参数索引仍保留，参数池可用计数仍为0，编码副本保持16M。

之后分别调用上一轮的原STOP消费函数：

- START_DONE在这个STOP消费者中返回0，但消息仍在队列，四类缓冲仍登记，未归还。
- STOP_DONE在相同人工上下文中清理四类索引、归还参数及消息缓冲。

这接通了原接收包装的局部发布与原STOP清理片段，尚未接通真实底层消息来源、完整START消费者、实际回调、请求代次或HAL完成。

## 边界与失败记录

待处理队列已满、借到的消息缓冲不足0x80、通道找不到owner时，均在原诊断前停止，不宣称完整错误收尾。某些失败发生在消息缓冲已经借出后，仍需追完整归还/取消路径。

保留了三个未通过的早期尝试：

1. 首次断言错误地比较不同PC处BL指令的完整机器字；已改为核对解码后的同一目的地址。
2. 执行范围漏掉0x228568末尾原跳转，严格执行器停止；已核对字节并将该原跳转纳入范围。
3. 早期预期MAIN提供可选指针就会调用回调，原执行否定了此预期。随后绑定真实stream谓词，并以全部25项对照、MAIN与非目标stream22分别验证，未修改原固件或伪造回调。

正式结果来自`run-20261025-stream-bound`；失败目录保留，不作为成功证据。

## 回执与下一步

- [正式结果](run-20261025-stream-bound/response-publication-results.json)、[摘要](run-20261025-stream-bound/summary.json)、[源指纹](run-20261025-stream-bound/source-receipt.json)。
- [脚本](response_publication.py)、[同agent复核](coordinator-observations.json)、[真实消息/MAIN消费后续锚点](next-main-completion-anchors.json)、[封存清单](final-receipt.json)。

在项目根复现，输出目录必须不存在：

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage40-response-types-and-publication/response_publication.py --output work/sony-firmware-20261024/stage40-response-types-and-publication/run-new
```

下一步追底层原消息生产/传输、MAIN的START与STOP各自消费者、实际owner注册、请求/配置代次、共享同步和全失败收尾。参数登记仍须在发布前建立，并覆盖停止完成前保留的数据与全部代码执行者。

52字节真实初始化、完整清零/诊断/start-input/有效HAL请求、上游FF质量与16M模型/query/cache/mux、实际主录/音画/长录/温度、同机健康备份、受限恢复/回读、WBI/冷启动和独立救援继续待验收。本轮未尝试UU/Windows或任何主动相机访问、模块、WBI/刷写，持续目标未完成。
