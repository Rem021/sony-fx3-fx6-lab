# FX3 timing Open 准备与参数写入所有权

本阶段运行了timing普通Open的实际参数准备动作0x194de8，**目标0x98字节视频参数和外层FileFormat15在输入组件调用之前保持不变**。目标帧率枚举3/逐行标志1选中已有的低帧率逐行接口，名义标量为30；原UHD59.94控制进入另一接口。

这还不是输入组件或硬件接受。非法codec但合法帧率的对照也能到同一边界，说明当前片段没有完成编码支持检查。另已核对SET_REC_FORMAT与Open写同一份整包存储；真正执行顺序、下游资源/VCD和回复仍待验证。

## 公开规格基线

2026-10-25重新核对的Sony原文页面明确标为经典ILME-FX3 Ver.2或以后。其代理设置列出1920×1080、HEVC/H.265、4:2:0 10-bit、16/9Mbps，并说明代理与电影录制同时进行。这里是代理能力基线，主录目标仍需独立证据。[Sony FX3代理设置原文](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000882045.html)

## 原Open动作如何准备输入请求

0x194de8是timing Open处理表的数值状态2动作。独立的“该动作已可执行、所需构造字段已建立”fixture中，它会：

1. 将输入事件内联的0x98视频包复制到timing对象+0x38，保存外层FileFormat到+0x2c。
2. 从raw packet+0x64/+0x89选择局部mode标量；这些字节的完整语义仍未绑定，本轮不为它们补上未经证实的菜单名称。
3. 依据packet+0x81和+0x80选择timing子接口，使用原表计算名义帧率。
4. 构造0xd4字节下游事件，复制0x28头部与原0x98视频包，将参数指针改为事件内联包，并补充局部mode、名义帧率等尾部字段。
5. 调用0x1454f4的 `sfmc_enc_input_if` 参数准备入口，本轮在入口之前停止。

没有执行前置状态转换、时钟查询、输入组件准备、资源申请或硬件Open。事件尾部一个原输入字的语义未知，使用显式fixture核对其原复制；不将其当作真实机身信息。

## 帧率接口选择与对照

原帮助函数0x194d24读取已复制的帧率和逐行标志，原名义表0x314860为24、24、25、30、50、60、100、120、200、240。

| 输入片段 | 原选择 | 到达边界 |
|---|---|---|
| 目标HD、frame3、progressive1 | timing+0x448，名义30 | 输入组件准备入口；视频包和FileFormat15不变 |
| 匹配proxy参数、FileFormat18 | 同上 | 视频包和FileFormat18不变 |
| 原UHD59.94、frame5、progressive1 | timing+0x420，名义60 | 视频包不变 |
| 只把codec改成0xff，frame3仍有效 | 同目标接口 | 同样抵达入口，不能当codec支持证明 |
| codec/frame均0xff | 原诊断路径 | 首个诊断调用之前停止，未解释完整错误结果 |
| raw64=1的独立fixture | 局部mode2 | 其它目标视频字节保留 |
| raw89=1的独立fixture | 局部mode3 | 同上 |
| progressive=0的独立fixture | timing+0x3f8 | 仅控制输入，不代表该HEVC组合被支持 |

子接口的原类型信息为timing模板模式6/7/8；低帧率逐行一支对应模式8。这里只按实际字段/分支描述，不把模板模式编号等同编码格式编号。

名义标量30不改变此前确认的目标有理时基30000/1001，也不是精确30.000fps或实际硬件时钟证据。8个Open动作场景均保持这一范围。

## 两条动作写同一份参数

原SET_REC_FORMAT前缀0x1956e0把其内联0x98视频包写到同一timing+0x38，并把FileFormat写到同一+0x2c，随后继续到未执行的配置命令构建器0x195724。

一个独立的三段顺序对照执行了“其它配置前缀→目标Open准备动作→其它配置前缀”。对同一客体存储，所保存的视频包/外层身份依次变成其它fixture、目标HD/FileFormat15、其它fixture。这是原整包写入的覆盖范围。

该对照的其它配置包和FileFormat5是明确的替代fixture，不是已验证的真实SET_REC_FORMAT输入。顺序由实验显式安排，未执行真实状态机调度，也未执行配置后半段。因此不能据此判断机身存在竞态或错误顺序，更不能直接提出一个常开覆盖补丁。

后续实现需要证明真实配置/请求顺序、目标参数的当前代次、各消费者持有者和完成条件。只证明某一次Open包正确，不足以证明最终使用的配置仍正确。

## 下一层入口

原输入组件0x1454f4会继续调用0x134568、0x1466d8（至0x148d3c）和0x141524；其后还有0x145530。它们的原指令作为静态锚点保留，本轮没有执行。下一步优先核对这里的字段复制、物理/逻辑缓冲与编码请求，以及SET_REC_FORMAT后续0x195724如何处理共享参数和完成回复。

硬件Open/Start是否接受目标、实际码流、码率/音频/时间戳与长录温度仍未知；已有低帧率接口不能替代这些结果。

## 验证与复现

首次正式运行通过：8个独立Open场景及1个三段共享写入顺序场景。原av-cam SHA256仍为 `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf`，输入前后哈希一致。

工具只为当前动作读取的字段准备明确fixture，不运行整套构造/配置。原映像只读，写入只准客体栈与fixture；未知调用、诊断及非法内存停止，没有修改返回值、跳过未知后台或执行宿主固件库。

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage31-timing-parameter-ownership/timing_parameters.py --output work/sony-firmware-20261024/stage31-timing-parameter-ownership/new-run
```

输出目录必须不存在，写入前验证目标卷UUID。

- [摘要](run-20261025/summary.json) · [原指令、类型信息与完整结果](run-20261025/timing-parameter-results.json) · [来源收据](run-20261025/source-receipt.json)
- [协调复核](coordinator-observations.json) · [阶段前目标](goal-status-before.json) · [阶段后目标](goal-status-after.json) · [持续目标](../GOAL_STATUS.json)

完整目标继续为经典FX3 7.02的MAIN 1920×1080、30000/1001、HEVC420 10-bit约16Mbps；精确30.000fps另列。源身份/OSAL/地址传输、真实状态/时钟、输入/资源/VCD与回复、同机健康备份、受限恢复/回读、独立救援、WBI/冷启动和真实成片/长录/温度及回归均未完成。

Windows/UU仍等用户通知恢复。本轮无新远程连接或任务发送，无相机接口、认证、切模式、驱动、机身/卡文件、模块、WBI或刷写；授权仍仅缓存PnP，目标保持active。
