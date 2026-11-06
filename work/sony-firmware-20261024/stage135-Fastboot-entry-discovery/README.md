# FX3 Fastboot：当前识别测试与进入条件

2026-10-27。用户提出“尝试测试……F33可不可以进入Fastboot模式”，按当前经典ILME-FX3理解，并确认目前只有Mac和Windows电脑。Windows仍按此前指示延后，本轮只用Mac。

**已完成实际Fastboot设备识别，尚未执行进入Fastboot模式。** Google官方主机工具37.0.1执行 `devices -l` 成功返回，但设备列表为空；前后Mac缓存均显示一台FX3，当前接口为MSC 08/06/50，没有标准Fastboot接口ff/42/03。这只能说明当前状态，不证明FX3永远不能进入某种兼容入口。

## 本轮实际操作

| 步骤 | 结果 | 范围 |
|---|---|---|
| 当前IORegistry缓存检查 | FX3 054C:0DA1，接口0为08/06/50；全厂商标准Fastboot签名节点0 | 原始树及序列号未保存，不打开相机文件 |
| 主机工具准备 | 从Google官方链接取得Platform-Tools37.0.1，Fastboot为37.0.1-15733141 | 仅放本任务目录；不改PATH、不装驱动、不启动ADB |
| `fastboot --version` | 成功 | 主机版本查询 |
| `fastboot devices -l` | 返回0，stdout/stderr均为空，设备行数0 | 实际枚举；进程网络被sandbox禁止；不执行模式或分区命令 |
| 枚举后缓存检查 | FX3仍为普通MSC；标准Fastboot签名节点0 | 同一授权范围的状态复核 |

实际命令回执见[actual-fastboot-enumeration.json](actual-fastboot-enumeration.json)，缓存见[枚举前](current-fastboot-cache-check.json)与[枚举后](post-enumeration/current-fastboot-cache-check.json)。缓存采集器中的“已知工具路径不存在”只指常见系统安装路径，不包含这次放在任务目录的工具；实际运行版本以上述命令回执为准。

Google工具来源为[官方Platform-Tools页面](https://developer.android.com/tools/releases/platform-tools)。标准USB匹配依据为[AOSP Fastboot源码](https://android.googlesource.com/platform/system/core/+/refs/heads/main/fastboot/fastboot.cpp)中的ff/42/03接口条件。枚举可能读取USB描述符，不把它称作仅缓存查询；本轮未请求任何Fastboot getvar、reboot、boot、download、flash、erase、OEM或解锁操作。没有改变HOME或全局配置。

## 公开Sony相机项目里的Fastboot从哪里来

[A7 IV原项目](https://github.com/DavidBuchanan314/ILCE-7M4-RE/tree/2328d18ce640e6c8cd9341efcf0043ce9042a135)明确针对ILCE-7M4。其流程是：

串口BootROM触发 → 加载自制RAM载荷 → 初始化硬件 → USB Fastboot

这不是已证明存在于FX3固件中的通用按键模式。固定提交的代码显示：

- 串口工具目标是Waveshare RP2040-Zero，使用RP2040 PIO。用户当前没有开发板或串口工具，普通电脑USB线不能直接代替该桥接硬件。
- 自制Fastboot载荷在USB就绪前调用CP启动、eMMC初始化、USB PHY和DWC3初始化。加载它本身已经是硬件状态操作，不能以“还没发flash命令”判断整条路径无副作用。
- 参考载荷使用18D1:4EE0及ff/42/03，故本轮检查没有只过滤Sony VID；当前仍未见其标准接口。
- 原项目的boot0透明加密处理尚有限制；A7 IV公开能力不能当作FX3恢复保证。

上述源码只下载、解压和静态读取，未构建、上传或执行。逐文件SHA和行号见[进入路线源码审查](Fastboot-entry-source-review.json)。没有提取或尝试使用相机密钥。

## 当前能否继续试“进入”

现有电脑已经足够执行标准Fastboot识别；它们目前没有把FX3切进Fastboot的已验证命令或通路。公开串口路线还缺桥接硬件，并且FX3仍需核对接口电气特性、ROM触发、RAM布局、CP/eMMC/USB/WDT初始化和退出/冷启动返回。不能仅凭同SoC或A7 IV源码向FX3加载该载荷。

本轮没有按键组合猜测、短接、复位、服务认证、ADB重启、加载外机型载荷或修改启动标志；没有完成进入/退出或救援验收。后续按用户已提出的进入测试意图继续收敛FX3专用步骤，不重复索要同一设备识别授权。是否需要相机侧模块/硬件操作，要以具体可复核方案及其范围为准。

原MAIN 1920×1080、30000/1001、HEVC42010约16Mbps目标、同机健康备份、原字节恢复与独立救援要求均保持。本次设备列表为空不代替这些验收，也不消除阶段134的服务登记副作用问题。
