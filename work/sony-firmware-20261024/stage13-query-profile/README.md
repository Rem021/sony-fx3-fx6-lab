# FX3 7.02 查询参数与定点原型的一致性

本阶段是 CPU-only 工程验证。查询 helper 的实验分支已与阶段12的定点 builder、setter 参数一致，**没有运行完整状态／剩余时间调用者、相机编码、录像或恢复**。

## 已验证的范围

- 新分支仅接受 format6、typed HS frame2，且原厂普通 movie 判定返回真。原普通帧率25p、非目标格式和 S&Q 不由该分支接管。
- 原厂查询函数执行真实模式判定、哈希桶查找和结果写入；本阶段没有模式或查找结果 adapter。哈希容器由原厂 `0x39898b0` 的26对常量构造，是合成输入，不是相机快照或实际 C++ 初始化结果。
- 30项原查找函数测试（26个已知键、4个缺失键）通过。
- 19个原版合法 HS 组合的查询结果与阶段12实际 setter 输出一致，启用分支后保持一致。
- 37个目标查询输出 VPC6／VQuality6／Frame3；32种旧质量值与6种普通 movie 模式别名分别覆盖，未穷举它们的笛卡尔积。
- 9组非目标控制保持相同观察结果。其中部分原路径因合成输入不完整而停止，不能当作其它格式的完整合法组合验收。
- 目标查询三元组与阶段12 builder／setter 实际客体结果一致，继而进入真实 MPR 参数准备函数，得到 stream0 codec15、1920×1080、42010、原始 bitrate 值16000、30000/1001。

MPR 阶段仍沿用阶段12的单地址日志适配器：只记录并执行 `PC←LR`，不写返回寄存器或输出。查询阶段没有这类适配器；到断言入口即停止，不执行断言处理或伪造成功。

客体代码位于独立 scratch 页，不是已核验的机身代码洞，不输出修改后的 ELF、安装包或相机 payload。原 ELF、既有实现和封存结果的哈希保持不变。栈临时保存按16字节操作，并检查原函数返回时 SP 与被调用者保存寄存器已恢复。原理参考：[Arm 栈帧说明](https://learn.arm.com/learning-paths/servers-and-cloud-computing/exploiting-stack-buffer-overflow-aarch64/frame-layout/)、[Unicorn 官方 FAQ](https://github.com/unicorn-engine/unicorn/blob/master/docs/FAQ.md)。

## 重现

在 Mac 项目根目录运行，输出目录必须位于本阶段内且尚不存在：

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage13-query-profile/query_profile.py --output work/sony-firmware-20261024/stage13-query-profile/new-run
```

程序先校验 KAFU2T UUID、官方 ELF 和固定依赖；仅执行有指令／时间预算的客体函数，未知代码、系统指令及非法访问停止。不会转发 USB、设备、文件或 MMIO 操作。结果位于 [首次运行摘要](run-20261025/summary.json) 与 [完整结果](run-20261025/query-results.json)。

## 仍未完成

1. 状态和剩余时间的完整调用者、卡容量／文件开销／音频等实际估算；共享转换 helper 一致不代表剩余时长已验收。
2. 菜单可选身份、固定16M／10bit显示、产品允许组合，以及设置保存／重入。
3. 模式生命周期：普通 movie 之外的部分输入仍走原断言。特别是“保留原有控制结果”不能证明新 profile 保存后切到 still、S&Q 或重启都安全，完整调用上下文仍须验证。
4. 将来回退旧程序前的 stock 合法设置恢复。内部 key 不等于持久存储或备份地址。
5. 同机健康备份、真实 USB／认证、WBI、硬件 Open／Start、主录文件、音画同步、长录、冷启动及对应范围恢复。

本阶段观察中 UU 仍显示服务器错误与设备离线，没有传输缓存包或执行 Windows 任务。这只是缓存关联采集的外部依赖；离线工程仍有后续工作。现有相机授权仍仅 Windows 缓存 PnP，主动查询与所有写入均未开放。完整目标保留在 [中央进度清单](../GOAL_STATUS.json)。
