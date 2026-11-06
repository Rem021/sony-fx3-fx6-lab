# 待继续：初始 MSC 与服务模式认证分支

本目录是阶段144用户授权插入前开始的**未封存离线工作**，不是可上机认证工具。原 `goal-status-before.json`、`readme-before.md` 是阶段142快照，当前主状态已经推进到阶段144；以后发布本目录结果前必须重新核对主状态并保留旧快照，不能把这些旧文件直接写回。

实际一次 USB 描述符读取已经在 [阶段144](../stage144-single-Mac-descriptor-trial/README.md)完成，权限已消耗并关闭。本目录没有任何相机或 Windows 操作。

目前明确的证据差异：固定 PMCA `SonySenserAuthDevice.authenticate()` 在 PID0336 时使用全部512B挑战与该轮材料，其余 PID 使用挑战前4B；阶段141提供者只有前一算法且无模式参数。阶段141六轮控制器夹具对 MSC 与 SERVICE 都调用同一个 `libsencore::xxstep`，因此不能证明真实初始MSC路径。服务原校验算法与公开材料逐字节对应的结果仍成立。**PMCA分支本身也不证明经典FX3 7.02实际使用前4B算法，仍须追踪原路径。**

从固定原固件镜像新提取三个候选作为数据，见 [MSC-original-candidates.json](MSC-original-candidates.json)：`usbg_storage.ko`、`libUsbControl.so`、`libusbcmd.so`。镜像与Ext2读取器均先核对既有SHA，没有挂载或执行原生Sony代码。符号名扫描只见SCSI sense及一般初始化，尚未定位初始摘要验证器，不能把名称未命中当作算法不存在。

下一步追踪原MSC厂商控制回调、其注册/事件去向与摘要验证者；核对是否由另一处理器或未命名代码处理。确认后为提供者加入显式模式分派，并用对应原验证者/准确参考分别测试，不能继续用一个服务验证器代替双模式证明。真实传输及驱动接管/归还仍需后续具体方案与新增授权。

补充原始社区线索，仅作待核对参考：

- [FX3A #715](https://github.com/ma1co/Sony-PMCA-RE/issues/715)中，2026-06-04首报macOS服务认证超时，作者在2026-06-09后续又报告同Mac改换依赖环境后成功。对象是FX3A 2.02，不能套用经典FX3 7.02；完整后续与所改代码尚未采集复核。
- [A7 V #677](https://github.com/ma1co/Sony-PMCA-RE/issues/677)首报不同USB口出现I/O错误或挑战9，并报告重启。它说明相同公开工具也存在机型/路径差异；不是本台FX3失败案例，更不是救砖保证。

后续不要重跑阶段144主动读取，不自动启动 `serviceshell`、Zadig、驱动安装或模式切换。
