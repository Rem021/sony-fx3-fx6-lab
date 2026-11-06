# Scrapling调查结果与FX3下一步

2026-11-01。官方技能及Scrapling0.5独立环境已核验可用，已实际抓取Sony官方页面、相关相机项目和libusb源码。[来源及复核记录](../../work/scrapling-research-20261101/README.md)。

## 新增的HEVC实现参考

[chocotan/a7c2-re的11月1日成果](https://github.com/chocotan/a7c2-re/tree/d79257cf6815642b9794fa5b590c9626bfbc2c67/report/2026-11-01-hevc30-ntsc-retest)针对A7C II 2.01的**4K29.97／25p**，不是FX3的1080p模式。作者把菜单、画质、限制、参数生产者和消费者一起接通；新发现的两处遗漏分别涉及系统频率及远端状态通知，即使不连接遥控端也可能在选择帧率时触发。

这为FX3提供了明确的核查方向：不能只改菜单或编码参数换算，还需对照全部消费者。该成果目前的通过证据是VM菜单往返；真实编码、媒体文件及稳定性仍未验收。作者也报告过真机切格式重启，但尚无足够故障栈证明与VM异常同因。

[封包说明](https://github.com/chocotan/a7c2-re/blob/d79257cf6815642b9794fa5b590c9626bfbc2c67/report/2026-11-01-hevc30-ntsc-retest/PACKAGING.md)明确：已构造和离线核对p15与DAT，但修改包没有有效Sony签名，本轮未安装真机。不能把完整生成器、校验正确或VM截图当作安全刷入证明。

## 恢复资料的适用边界

[A7C II故障讨论](https://github.com/QAQLeonard/a7c2-fl23-research/issues/31)中有用户通过仍能运行的录像路径重新进入系统；维护者说明那批修改在拍照逻辑中。这类旁路不保证能覆盖FX3视频链、引导区或存储损坏。

[Sony FX3 7.02官方说明](https://www.sony.com/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx3/software/00298561)提供了特定更新文件／版本顺序错误下的换卡重试步骤。它不是任意启动损坏后的独立恢复接口，当前也没有必要让已是7.02的机身重新升级。未操作相机卡或下载新固件。

## 本次真实USB故障的新线索

[通信02实际记录](../../work/sony-firmware-20261024/stage269-recovered-communication02-execution/README.md)证明MSC交换及SERVICE端口关联已发生，但主机获取SERVICE时返回独占访问错误，未到SERVICE认证和88B读取。

通过Scrapling抓取并固定的[libusb Darwin实现](https://github.com/libusb/libusb/blob/987c1170d0018ba82557823a98ae443e8335e11b/libusb/os/darwin_usb.c#L1939)将设备层独占打开失败与仍可进行的后续操作分开处理。我们的复合获取当前将相关非零返回视为失败，但实际失败子步骤未写入回执。这支持优先补足分步骤证据、审查设备与接口的不同打开语义；并不证明可以忽略错误或抢占其他应用。

缓存还显示Chrome、ChatGPT及本helper同时存在device userclient。客户端存在不能确定独占访问的持有者，未关闭应用或执行额外设备试验。

下一步先按用户屏幕／访问灯反馈完成本次恢复收尾，再对照上述实现修正主机接口适配；HEVC支线补查系统频率和远端通知消费者。完整同机备份、独立恢复、硬件主录及首刷条件仍未通过。
