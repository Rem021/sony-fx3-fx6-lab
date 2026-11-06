# FX3 默认 Backup 双记录与 GPIO 参数

2026-10-29；经典 ILME-FX3 7.02；仅本机已有固件文件的离线研究。

本轮解出了经典 FX3 的11份地区默认模板，并确认 GPIO 两个参数的名字，但**尚不能把任一组默认值作为实机恢复载荷的配置**：每份模板都有两份有效记录，同样的三个属性在两记录中的数值不同。下一步需要追到 Backup 服务实际使用哪份记录。

| 官方 AP 程序读取的属性 | 已知用途 | 记录0（文件偏移0） | 记录1（偏移0xD2000） |
| --- | --- | --- | --- |
| F900D4 | `/dev/sio%d` 的数字后缀 | 0 | 5 |
| F900B1 | `UdtrGpioOpen` 参数1，portid | 4 | 4 |
| F9006D | `UdtrGpioOpen` 参数2，bitnum | 2 | 30 |

以上是**公开升级包的出厂默认模板**，不是这台相机的 Backup.bin、引脚测量或连接回执。记录0恰好与 A7 IV 参考载荷的0/4/2相符，只能作为线索。两个记录都通过校验，不能因另一组不符合参考值就舍弃它，也不能先把二者命名为 AP/CP 再据此选值。

## 模板格式与独立核对

原件来自既有解密官方7.02 FDAT中的 `0110_backup/SYSIPSX-DSLR/ALCIN/CX959*.bin`，共11份，每份2,229,740字节。逐份按原偏移、SHA-256和CRC32回核；保留原件，不混用 `ALCIN_HIBIKI2`。

采用维护者的 [PMCA BK4格式定义](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/backup/__init__.py)，固定提交 `a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0`。自写只读解析器检查了22份记录的声明范围、校验和以及735,515个属性表条目的当前数据范围；只导出上述三个已命名属性。记录0长857,900字节，记录1长1,369,580字节，中间2,260字节为零填充。每份记录均有819个 subsystem；两记录属性表分别有35,668和31,197项。

随后只加载已核对的 PMCA `backup`、`util` 两个主机解析模块，对只读内存缓冲区交叉检查22份记录、66个属性实例，全部一致。没有加载 PMCA USB／运行时模块，没有调用写入方法，也没有执行 Sony 固件或机身代码。这证明格式和值的解析结果吻合，不证明相机会使用哪份默认记录。

证据：[原件捕获](template-source-capture.json)、[两记录结果](template-field-results.json)、[PMCA交叉核对](PMCA-reader-crosscheck.json)、[只读解析器](read_template_fields.py)。

## GPIO 参数的实际含义

从官方7.02主系统 p15 的 `/lib/libul_GpioCtrl.so` 重新读取并核对既有原件，SHA-256为 `49904397517841f9be3ddda6c359d0391eb9ab726a02aa891ca1f97976550548`。

`UdtrGpioOpen` 在0xB14/0xB18保存参数1/2，0xB2C/0xB30将二者作为单字节写入 handle+12/+16。0xB64—0xB70复制从 handle+8 开始的16字节结构到 ioctl 参数。库自身的诊断函数0xAA0—0xAF8把该结构+4命名为 `port.portid`，+8命名为 `port.bitnum`，因此两个入参的含义已有原始指令与字符串对应。

官方 AP helper 传入的模式2，在该库0xBC8后的分支中转为控制值9，并调用 ioctl `0xC0104702`；对应错误文本明确写 `GPIOMODE_GPIO | GPIOMODE_OUTPUT_H`。这是库对该调用的静态解释，未验证当前机身驱动的执行结果或真实引脚电平。

历史2.04/2.05 p1提供库的 `.text`、`.rodata` 与该主系统库相同；整文件7字节差异都在不加载的 `.comment` 区。这个比较不能代替当前机身7.02 p1库指纹。当前Ubody未单独携带该库，也不等于库在所有运行环境中不存在。

证据：[GPIO原始范围与参数证明](GPIO-layout-proof.json)、[核对脚本](prove_GPIO_layout.py)、[7份原始切片](pins/)。Ver7.00的公开 GPL GPIO片段仅涉及中断／寄存器参考，不是本次 ioctl 的完整字符设备实现，不据此宣称当前驱动已验证。

## 尚未闭合的关键关系

既有 `/lib/libbackup.so` 的 `Backup_read_4Byte` 包装在0x1E14，构造请求0x003E014D、4字节长度并转交服务。包装中没有 Backup 文件两记录的选择逻辑；另有 `interchip` 接口的存在也不能单独证明记录角色。本轮仍保留 `selected_source_record=null`，下一步追实际服务接收者及记录选择。

即使后续确定默认配置，恢复路线仍需当前同机启动链、p1原件、实际入口／传输、备份、逆写和独立恢复验收。当前尚未证明 MAIN 失效后能够独立恢复，也未开始首次修改固件刷入或1080p29.97 HEVC主录／长录验收。完整16项要求保持原状态。

195轮仅主机 root01 的具体批准仍待答；本轮没有启动该程序、没有重问。没有新增 USB／缓存查询、管理员／驱动操作、Sony认证、相机文件访问、载荷上传或固件写入。所有旧单次试验的消耗与 UNKNOWN 记录保留。

## 回执

- [核查回执](verification-receipt.json)、[实施边界](implementation-review.json)、[解析修正记录](analysis-corrections.json)、[来源核对](web-source-review.json)。
- [前轮 MCU读取与配置来源](../stage206-FX3-MCU-read-protocol/README.md)、[0.4恢复适配工具](../../../outputs/fx3-recovery-adapter/README.md)。工具发行物未改动，本轮只补恢复配置研究证据。
- [本轮封存清单](final-receipt.json)记录全部本轮成员与哈希；动态进度和项目索引只以本轮快照参加封存。
