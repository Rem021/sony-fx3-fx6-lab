# Sony 公开固件目录实测：FX5／FX5B 供体查询

2026-10-30 UTC。本轮已打通一条可匿名复现的 **Sony 官方目录 → 固件信息 → 原厂下载地址** 路径；FX3、α7 IV 正对照均成功。**FX5／FX5B 在本轮输入下仍只有空版本、空 ID、0 字节，未取得完整私有供体。尚未产生可刷入的修改固件，整套专业菜单／VENICE ISP 移植目标没有完成。**

本轮从重启前已经下载的固定提交继续，未重下源码、未重跑历史解包或签名实验。外盘 UUID 已核对，项目根无 Git 仓库。旧封存阶段与另一 owner 的设备、HEVC、加载／恢复实现保持原位。

## 实际找到并验证的接口

线索来自 [CameraSync 固定提交](https://github.com/rock3r/CameraSync/tree/c25814716a15afca997e0abf0a661974c5021669)，仅阅读其源码，没有构建或运行应用。该仓库的每日 GitHub Action 更新的是 **Ricoh** 数据；Sony 检查器直接调用 Sony 在线 API。初步将两者联系为同一更新目录的推断已纠正。

- POST 目录：`https://support.d-imaging.sony.co.jp/FSErFHP8Je0xINMFVv9P/api/firmwarelist_api.php`
- JSON 字段名必须按实际序列化源码记录为 `ModelList`。本轮使用普通研究 User-Agent、JSON Content-Type，无账号、Cookie、Authorization 或设备连接。
- 实际响应字段为 `firmwareInfoAPI`、`firmwareID`；随后的 GET 参数为 `fwid`、`area=pmm`、`lang=us_en`，返回 `fwURL`。
- 已执行 10 次目录查询、2 次信息查询，12 个请求均 HTTP 200；各自保存请求、原始响应、可读 JSON、时间和 SHA256。所有查询版本均是明确声明的分析输入，未冒充机身版本读数。

源码归档 3,573,085 字节，SHA256 `f2481199ea1a8fa50eff8e0e3b5299f908fe5e99fb253b9c96461b3c92184017`；19 份选定文本已逐一与归档成员核对。

## 查询结果

| 型号／分析输入版本 | language 参数 | 固件版本／ID | 大小 |
|---|---|---|---:|
| ILME-FX3／7.00 | en_US、us_en | 7.02／953 | 811,876,768 B |
| ILCE-7M4／6.01 | en_US、us_en | 6.02／963 | 757,480,856 B |
| ILME-FX5／1.00 | en_US、us_en、jp_ja | 均为空 | 0 |
| ILME-FX5B／1.00 | us_en、jp_ja | 均为空 | 0 |

另有初始多型号 `0.00` 查询，仅返回一个空 FX5 条目、没有返回两台已知型号。它不能单独充足够的负对照。后续拆成单型号并用已知旧版本，得到了上表的正对照。因此本轮负结论以成功正对照及具体输入范围为限，不解释服务器为何省略 `0.00` 控制项。

FX3 信息查询实际给出原厂 `BODYDATA.DAT` URL；跟随其公开重定向后，64 字节 Range GET 返回 HTTP 206，`Content-Range: bytes 0-63/811876768`。这 64 字节与现存经典 FX3 7.02 原件相同。**没有重下完整包；前缀与总长度相同不证明全文件身份，更不证明修改包会被接受。** α7 IV 也返回 BODYDATA.DAT 地址，仅保存元数据，未下载其二进制。

FX5 系列没有可用 firmwareID，未猜测或遍历其他 ID，也未以空 ID 请求包。API 包装字段中的 `date=2023-01-24` 不是本轮固件发布日期；观察时间以各 HTTP 回执为准。

## 对移植目标的影响与证据边界

1. 新增了经过正对照的供体查找入口，但未获得 FX5 私有菜单、实时 ISP、RAW 采集或传感器校准载荷。空响应只说明这组公开接口输入没有给出包，不能推出全网不存在包，也不能证明 FX5 受消费版 Creators’ App 支持。
2. [Sony 官方 FX5 日本下载页](https://support.sony.jp/electronics/support/camcorders-and-video-cameras-interchangeable-lens-camcorders/ilme-fx5/downloads)仍写明本页没有提供更新信息。本轮保存了 HTTP 200 原始页及摘要。
3. [FX5 官方维护菜单](https://helpguide.sony.net/ilc/2630/v1/en/contents/maintenance.html)描述固件更新菜单，不提供可直接分析的私有载荷，也不建立跨型号或修改包兼容性。FX5 文档另有 [Creators’ App for Enterprise 定位功能](https://helpguide.sony.net/ilc/2630/v1/en/contents/location_info.html)，不能拿消费版接口的空值排除所有专业更新渠道。
4. [Sony 消费版 Creators’ App 更新说明](https://helpguide.sony.net/di-app/ca/v1/en/contents/CA_update_software.html)要求在应用内登录。本轮确认上述目录／信息 HTTP 请求本身匿名可访问；未执行应用更新流程或登录。
5. 既有 VENICE 内层未因本轮公开目录查询而变得可读。既有原厂 RSA2048／SHA256 验证及单字节修改失败结果按原摘要保留，未重跑。获得原厂下载地址不能充修改包准入证据。

[证据核查](evidence-audit.json)保留原 9 项完整要求：FX5 私有供体、VENICE 完整 ISP、实际 RAM／DMM、CMOS RAW／校准、专业菜单与 MAIN 录像、具体修改包、经典 7.02 修改包准入、正常启动与独立恢复、实际刷机前停止。所有功能完成状态维持未证／缺失；最后一项操作边界继续保持。

用户恢复后开始新的阻塞计数，本轮为首次，不沿用之前的三次计数。原生目标回读为 active，未标完成或暂停。当前真正缺少的仍是可读完整私有供体／适用解析器，以及经典 FX3 修改包准入与恢复证据。

## 复核与保全

- [源码来源与摘要](source-capture.json)
- [初始目录请求](anonymous-list-query/receipt.json)
- [单型号正负对照](control-queries/all-receipts.json)
- [已知 ID 与 FX5B／日本参数核对](known-info-and-model-variants/all-receipts.json)
- [官方页面快照](official-documents/capture-receipts.json)
- [64 字节读取范围与本机对照](official-documents/fx3-bounded-prefix-receipt.json)
- [离线证据核查](evidence-audit.json)、[目标状态回读](goal-status-verified.json)

离线核查脚本 `audit_catalog_evidence.py` 验证原始响应与回执摘要、19 份来源成员、12 个元数据请求、正负对照、4 份官方页、64 字节 Range 范围、此前 9 文件封存和两份签名证据。网络采集脚本拒绝覆盖现有采集目录；复核不需要重复发送请求。

无相机／USB／BLE／手机／相机 IPC／机身写入，无原生 Sony 更新程序执行，无私有签名密钥工作。原件、旧回执和其他 owner 文件未修改。本阶段与项目入口的新增记录是本轮唯一项目写入范围。
