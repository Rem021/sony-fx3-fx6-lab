# FX3：STOP完成通知、原回调与输出状态队列

本轮33段原代码片段的离线验证通过。MID`0x113`接收分支经原回调和分派器进入输出状态机的`codec_stop_comp_v`事件。忙碌输入下，原接收函数可以返回0，STOP事件仍在队列中；单个视频完成事件的原状态表也可能只选择下一停止阶段。

另一处原STOP命令动作能构造与`enc_stop_done`动作相同的通道通知包。因此，通知包、局部返回值或一个状态字都不足以单独证明整条链已经空闲、实验数据可复原或代码可卸载。

这些均为原映像上的受控客体输入。原运行时实例、完整构造、强制诊断、真实路由/队列/同步、配置代次、硬件与机身恢复仍未验证。本轮没有尝试相机或UU/Windows连接。

## 三层事件编号需要分开

| 层 | 本轮绑定 |
|---|---|
| 资源通知 | CID0x2103 / MID0x113，12字节，payload为通道号 |
| codec接口回调 | 原0x1388dc起分派接口事件0x1c |
| 输出状态机 | 原0x1500a4 →0x15391c/0x153938，内部事件18 `codec_stop_comp_v` |

这个内部事件18与较低IMOLA状态机的事件18 `enc_stop_done_t`属于**不同状态对象和类型**。不能因为编号相同而合并两个完成条件；较低层`ENC_INFRA_STOP_WAIT`也不是这里的`STOPPING_*`状态。

## 回调地址由原构造片段写出

本轮执行原输出状态对象0x155bd0构造前缀，写出STOP嵌入事件的原虚表、编号及待处理标志；在第一次运行时清零前停止。真实单例工厂和完整初始化没有执行。

另三段明确独立的原构造存储与一个原getter，分别建立组件→codec回调、codec回调→output回调、output回调→声明的状态holder关系。两处回调虚表及STOP嵌入事件虚表均由原指令写入，没有由宿主替换成自制回调地址。

- codec回调原地址点：映像+0x35bb68，RTTI为`sfmc_enc_codec_if::callback_handler`。
- output回调原地址点：映像+0x35edb0，RTTI为`sfmc_enc_output_if::callback_handler`。
- STOP嵌入事件原地址点：映像+0x35f408，RTTI包含`sm_output_`及`codec_stop_comp_v`。

对象/holder地址、owner、初始状态及活动字节仍是声明的fixture；原构造片段不能证明真实机身对象地址或生命周期。

## 接收前缀与独立正文的实际终点

原0x1386f4检查CID/MID并到达STOP分支的强制诊断前。然后本轮以捕获的寄存器和原保存栈，**独立**执行0x1388dc之后的原片段；没有执行或伪造诊断返回值，也不把两段称为完整接收过程。

它沿原虚调用执行0x134924 →0x14ff4c/0x14ff54 →0x1500a4 →0x15391c/0x153938。

通道7只用于与上一轮包的字节对照，是人工输入；本轮没有调用真实单例工厂或证明该通道对应MAIN登记对象，也没有验证外层实际消息如何选中接收owner。

在`STOPPING_AV`、活动字节为1的输入下，原代码实际：

- 将嵌入事件地址登记进输出队列，队列计数变1，STOP待处理标志变1。
- 原内部处理函数返回1；原包装函数执行`result == 0`，得到0。
- 从同一原PC继续，沿原栈返回到接收函数调用者；状态仍为`STOPPING_AV`，活动字节仍为1，待处理事件仍在队列。

这里的包装函数0不能被当成已完成、全局错误或全链成功回执。低层IMOLA包装函数的判定规则与此不同，必须逐个接口核对。

活动字节为0的`STOPPING_AV`与`STOPPING_A`输入均到达原退出动作的强制诊断前，状态尚未更新。原迁移、事件动作、新状态entry和真正停止未完成。

## 音频与视频完成的原表

本轮执行以下8个原next-state selector；只证明表的选择，不证明guard、动作、状态迁移或硬件接受：

| 输入输出状态 | codec_stop_comp_v选择 | codec_stop_comp_a选择 |
|---|---|---|
| STOPPING_AV | STOPPING_V | STOPPING_A |
| STOPPING_A | STOPPED | ERROR |
| STOPPING_V | ERROR | STOPPED |
| STOPPED | ERROR | ERROR |

两种完成顺序对应不同中间状态；视频通知本身不一定选择STOPPED。表中的ERROR目标也不是本轮实际发生的机身错误或已执行的错误处理，不能从人工重复事件推断固件缺陷。

即使完整迁移以后观察到STOPPED，也仍需核对IMOLA、音频、输出/mux、前端/工作线程与实验模块所有执行者；本轮没有建立全局安全点。

## 相同通道包的另一处原生产者

原`resource_video_enc_stop_param_t`表位于0x37f868；状态6 `ENC_READY`及状态10 `ENC_INFRA_STOP_WAIT`的原动作wrapper均跳到0x24c94c `action_stop_command()`，next selector均选择4 `ENC_IDLE`。本轮仅执行两个selector，未执行对应完整迁移。

另从0x24c994独立执行原包构造片段，通道7得到`032113010c00000007000000`，与上一轮`action_enc_stop_done_result()`构造的包逐字节相同；实际发送及强制诊断未执行。

因此，包本身不能区分这两处原动作，也不能证明收到的是某次新的`enc_stop_done_t`回执。真实接收owner、队列来源、状态顺序与请求关联可能由外层机制保证，本轮尚未绑定这些机制，没有断言原厂缺少校验。

## 回执与后续

- [正式结果](run-20261025/stop-routing-results.json)、[摘要](run-20261025/summary.json)、[执行源指纹](run-20261025/source-receipt.json)。
- [脚本](stop_routing.py)、[同agent复核](coordinator-observations.json)、[后续入口](next-output-stop-anchors.json)、[封存清单](final-receipt.json)。

在项目根复现，输出目录必须不存在：

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage45-stop-notification-routing/stop_routing.py --output work/sony-firmware-20261024/stage45-stop-notification-routing/run-new
```

接下来继续输出队列的原出队/两种完成事件的实际动作与退出、真正接收owner/配置epoch、较低层infra停止与seq_id生产/重用，以及所有消费者/执行者的退出。52字节初始化、真实start-input/HAL、模型/query/cache/mux统一、实机HEVC主录/音画/长录/温度、健康同机备份、受限恢复与回读、WBI/冷启动及独立救援全部保留，目标未完成。
