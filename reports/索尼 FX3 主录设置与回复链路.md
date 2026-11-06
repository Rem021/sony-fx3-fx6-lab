# 追通 FX3 回复链并约束主录修改

核查日期：2026-10-25。**FX3 7.02 的活跃命令查找、Jiritsu处理器和正常回复生成已接成有条件的静态链。** 新解析器也能处理与原厂主程序等长的分段合成回复。主录研究推进到了真实模型输入来源，并排除了一条会连带改变其他4K组合的常数修改。上述结果尚未证明当前机身可认证、完整读回或硬件录制。目标仍是可用的HD HEVC主录与对应恢复验收，不能用本轮离线通过代替。([本轮证据与验收清单](../work/sony-firmware-20261024/GOAL_STATUS.json))

## 活跃路由与正常回复规则已静态接通

现已追到运行时pFunc指针的赋值、外层`0x40`选择器、Jiritsu记录查找、OSAL回调及实际处理器。权限仍是独立门禁：level1拒绝这些记录，level2在相应标志条件下通过，level3走允许分支；当前机身的level及初始化状态未知。**这证明条件成立时的代码路径，没有证明真实USB通道已可用。**([活跃查找与权限原字节](../work/sony-firmware-20261024/stage10-mainpath/reply/final-reply-proof.json))

这里纠正stage9的记录起点：命令15应从family地址`0x31d98`开始，queueID在同一记录`+0x44`，步长为`0x48`。旧切片从`0x31d94`开始，前置u32实际是上一条记录尾；相邻记录queueID相同掩盖了结构解释错误。旧文件保留，新指令取址为准。记录高位`0x4000`是权限标志，与外层pFunc键`0x40`分开。([修正依据](../work/sony-firmware-20261024/stage10-mainpath/reply/selected-record-and-file-prefix.json))

回复采用12字节头，`+0x08`被写成3；PMCA将该字段命名为`version`，本报告不据此命名“FX3协议版本3”。分离缓冲路径每轮发送至多1MiB，size表示当前剩余payload；底层回调另限32KiB。成功plain文件读取的4字节状态只在整个逻辑payload开头出现一次。回调大小不能当成USB packet或结束条件。([原厂发送链](../work/sony-firmware-20261024/stage10-mainpath/reply/serializer-and-pfunc.json)、[PMCA字段定义](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L822-L876))

## 31项合成测试覆盖完整目标长度

新的纯字节重组器区分stage9全零合成profile与FX3静态候选profile，按remaining-size接续分段，并只解释一次状态。大响应须预先绑定精确manifest长度，首头、续头或尾部不符即失败锁止；最终确认完整前不公开成功结果。它只导入dataclasses、struct，没有设备backend或I/O。([自写解析器](../work/sony-firmware-20261024/stage10-mainpath/host/offline_reassembly.py))

**31项合成测试及协调端独立复核均通过。** 与原厂`appFw.so`等长的79,015,712字节生成数据，经76段重组，计数与摘要一致；这不是相机备份。大响应采用最大80MiB目标数据策略，暂存和返回还会产生副本，未实现流式落盘。精确长度也不能证明内容真实或排除等长损坏。([测试收据](../work/sony-firmware-20261024/stage10-mainpath/host/offline-fixtures.json)、[来源及独立复核](../work/sony-firmware-20261024/stage10-mainpath/host/source-receipt.json))

`finish()`仅表示给定离线capture完整。真实USB短返回、timeout、padding及ZLP仍未验收；libusb也明确区分请求长度、实际传输量和底层packet，不能把短返回直接当成文件EOF。([libusb同步传输](https://libusb.sourceforge.io/api-1.0/group__libusb__syncio.html)、[packet与overflow](https://libusb.sourceforge.io/api-1.0/libusb_packetoverflow.html))

## 真实模型入口已定位 常数替换不满足可用目标

已将普通主录setter的wrapper、sequence内嵌输入和带类型身份的builder对应起来。构造与发送位置相差`0x30`，能把builder的帧率、格式、质量、色彩字段映射到setter输入。完整产品能力、菜单允许组合与模型访问器尚未闭合，构造初值也不能当作最终设置。([模型来源与字段证据](../work/sony-firmware-20261024/stage10-mainpath/main/main-path-summary.json))

14例受限CPU仿真只运行真实setter的转换块，使用合成上下文。原版HS420目标形状输入得到VPC5／VQ6／Frame3；仅在Unicorn内将MOV5改为MOV6能得到目标VPC6，却连59.94／100M控制也一起改成HD。因此它只定位作用点，**不构成可用补丁**。4个异常输入在未知或断言路径隔离停止，不能解释为相机拒绝或崩溃。([逐例客体写入及边界](../work/sony-firmware-20261024/stage10-mainpath/main/setter-conversion-results.json))

本轮有离线guest固件函数仿真，没有执行完整builder、完整setter、MPR或硬件Open／Start。Frame3仍是30000/1001，即29.97fps；精确30.000fps尚未建立。([执行边界](../work/sony-firmware-20261024/stage10-mainpath/main/source-receipt.json)、[真实帧率转换证据](../work/sony-firmware-20261024/stage4-windows-collab/mac-verification/hd420-16m-chain.json))

## 下一步从模型选择形成精确目标组合

下一项离线工作应沿真实builder的typed getter、产品能力与参数选择分支，建立仅针对目标模式且与菜单、查询和编码参数一致的定义；同时把当前回复规则纳入受限诊断契约。实机身份与原件、认证和退出、当前WBI后端、完整回读、主录成片、长录及对应恢复／冷启动仍分别缺证。本轮未生成修改后的固件或刷写工具，未操作相机，授权仍仅Windows缓存PnP；完整验收要求已登记，持续目标未完成。([持续目标证据台账](../work/sony-firmware-20261024/GOAL_STATUS.json)、[本轮收据](../work/sony-firmware-20261024/stage10-mainpath/final-receipt.json))
