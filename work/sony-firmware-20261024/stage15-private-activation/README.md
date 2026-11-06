# FX3 独立激活状态：局部参数原型与配置一致性缺口

保留原厂合法帧率/质量设置，用独立实验开关选择目标参数，可以避开上一阶段发现的5个合成上下文错误路径。**这只是离线实现比较，尚无可上机的激活、保存或恢复器。** 完整菜单、持久化、冷启动、硬件主录及对应恢复目标保持不变。

## 已验证的局部行为

使用固定官方7.02提取件的原始AArch64函数，在Unicorn内执行3处自写分支。代码和开关都位于新建客体页；地址不是相机可安装位置，也未导出ELF、补丁包或刷机文件。开关仅由宿主设置合成初值，客体只读取，不执行相机设置写入。

| 对照 | 观察 |
|---|---|
| 19组原合法HS参数，开关关闭 | builder完整缓冲区与原厂相同，setter/query结果一致 |
| 同19组参数，普通movie且开关开启 | builder实际写出15/6/2/0，setter与query均得到6/6/3；原模型槽位保持原值 |
| 模式值0至4，保留合法frame0 | 开启和关闭均返回原厂结果，避开上一阶段保存frame2导致的错误入口 |
| 模式值5、6、7、8、9、15 | 启用后返回目标参数；名称仅按已证实的普通movie谓词解释 |
| 模式值10至14、16 | 开启与关闭的观察结果相同，但S&Q合成输入/其它依赖未闭合，不称已通过实际S&Q回归 |
| 3组其它格式/无效模式、2组无效开关、8组setter控制 | 与关闭时观察结果一致；未知开关值不激活实验分支 |

目标setter输出继续送入原MPR转换链，得到MAIN stream0、codec15、1920×1080、420 10bit对应字段、quality22、码率函数原始值16000以及30000/1001。仍是参数检查和Open参数准备，没有执行硬件EncOpen/Start。原始码率返回值不能直接标成16000 bit/s；精确30.000fps仍单列未实现。

查询的模式谓词和原查表指令实际执行，无输出适配器。MPR仅沿用已记录的单地址日志跳过：读取日志、PC回LR，不填返回值或输出字段。原件、依赖前后哈希一致。

## 负例决定了下一步必须处理配置所有权

完整8种二进制开关快照组合中，5种在builder、setter和query之间产生不同的编码参数。比如builder读到开启，setter/query读到关闭时，前者仍留下目标builder元组，setter却走原厂codec组合。即便使用原子变量逐次读开关，也不能自动使整条调用链一致。

另一个对照固定开关始终为1：先用普通movie模式5生成并转换目标参数，再分别以其它模式值调用query。模式0至4均成功返回原厂参数，与先前目标编码参数不同；普通movie6组相同，其余6组仍是依赖未闭合。这些是**分别构造的输入快照**，不是实际线程交错、模式转换或相机故障。

因此尚不能宣称独立开关已经解决整个生命周期。后续须找到真实调用者/线程/通知和录制空闲边界，使激活状态、模式、格式及其它系统条件在一次操作中使用一致配置。NTSC/PAL条件也尚未接入本原型；19组枚举对照不证明能在PAL系统强行启用29.97。

## 保存、重启与恢复仍需独立证据

- 新增开关的相机内存分配、初始化、所有者、UI入口、固定质量显示和保存策略均未实现。客体scratch地址不能复制到机身。
- 在模拟器中重新设flag=0，只证明这组输入返回原厂参数；不证明物理关机清除了私有状态。WBI可能保存/恢复RAM，必须另查真实生命周期。
- 本阶段没有改变原厂模型值，减少了“原值已非法、删除补丁后仍被原厂读取”的局部问题；这不等于已经拥有固件回退或救砖能力。
- 同机原件、健康检查点、受限恢复器、回读、冷启动和应用失效后的独立入口均缺实证；未诱发相机故障。

Sony官方说明，文件格式及视频设置在多种拍摄模式下都可显示，因此菜单状态不能只按录制入口处理。[菜单适用模式](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000888827.html)

官方Save/Load Settings用于设置文件，要求同型号，并提示固件版本差异可能导致加载失败；它没有给出本实验的程序/校准/启动恢复保证。这里将它与同机固件健康备份分开。[Save/Load Settings](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000884354.html)

官方Different Set for Still/Mv列出的分离设置项也未包含本实验开关，不能借该功能推定新增profile会被正确分离或保存。[Different Set for Still/Mv](https://helpguide.sony.net/ilc/2210/v1/en/contents/TP1000885439.html)

以上官方网页于2026-10-25读取，适用于经典FX3 Ver.2或以后帮助指南；它们没有证明实验分支能在实机工作。

## 重现与证据

```sh
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage15-private-activation/private_activation.py --output work/sony-firmware-20261024/stage15-private-activation/new-run
PYTHONDONTWRITEBYTECODE=1 work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/sony-firmware-20261024/stage15-private-activation/snapshot_boundaries.py --output work/sony-firmware-20261024/stage15-private-activation/new-snapshot-run
```

输出目录必须不存在。运行前校验KAFU2T UUID；局部客体限制指令范围、执行量和内存访问，不转发USB、系统调用、文件或MMIO。

- [主实验摘要](run-20261025/summary.json) · [主实验完整轨迹](run-20261025/activation-results.json)
- [配置快照负例摘要](snapshot-run-20261025/summary.json) · [负例完整轨迹](snapshot-run-20261025/snapshot-results.json)
- [主实验来源收据](run-20261025/source-receipt.json) · [负例来源收据](snapshot-run-20261025/source-receipt.json)
- [阶段前目标快照](goal-status-before.json) · [阶段后目标快照](goal-status-after.json) · [持续目标](../GOAL_STATUS.json)

用户表示稍后恢复UU/Windows连接，本阶段没有新增远程尝试、传文件或发送Windows任务。相机权限仍仅限Windows缓存PnP；没有打开设备接口、认证、切模式、安装驱动、读取卡或机身文件、WBI、刷写或实机测试。
