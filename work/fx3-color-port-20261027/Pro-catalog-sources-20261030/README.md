# 专业产品固件目录与 FX5 私有供体复查

2026-10-30。**已验证中国官方服务站的真实固件目录接口：它登记了 FX5、FX5B 两个型号，但全站和型号路径查询均返回空固件列表。** 正对照成功返回 FX6 6.01、FX3 7.02 和 VENICE 2 5.00 的下载条目。本轮未取得完整可读的 FX5 私有系统或新的 VENICE ISP，仍无可正常刷入经典 FX3 的整套专业菜单／色彩链修改固件。

## 重启恢复与来源

重启后先核对了外盘 UUID 与此前4批捕获中的12份实际源对象，摘要一致；没有发现这些采集脚本仍在运行，也没有待用户回答的问题。已完成的页面、脚本和控制查询均复用，随后执行尚未进行的全站／注册路径查询。

[Sony 专业站 FX5 产品页](https://pro.sony/ue_US/products/handheld-camcorders/ilme-fx5)的支持资源链接指向 `https://www.sony.co.jp/en/ILME-FX5/`。匿名 HTTP 沿此入口最终到达 Sony UK 产品页，本机抓取返回403；这不是“没有固件”的证据。网页读取工具能读到专业站的支持链接与计划功能说明，也不证明存在可下载的完整供体。

从[中国 FX6 官方固件页](https://service.sony.com.cn/download/firm/00002963.html)及型号页取得实际脚本URL，只阅读源码，没有执行网页JavaScript、登录或提交个人资料。页面模板中的“没有信息”占位文字不能作为查询结果；结果取自下列实际HTTP响应。

## 官方接口实测

| 入口 | 作用与实际结果 |
|---|---|
| `outProduct?method=findProList` | 从FX6页面给出的ILME系列路径读取12个登记型号，包含FX5、FX5B、FX6V、FX3 |
| `outDownload?method=findPage` | 使用源码中的固件分类及型号名查询；FX5／FX5B的Data为空，正对照有真实条目 |
| `homePageExt?method=findDownLoadPage` | 使用返回的FX5／FX5B完整注册路径再次查询，Data仍为空 |
| `outDownload?method=findOne` | 从返回的固件路径读取下载URL和条目信息，不猜测或遍历ID |

12次JSON API请求均已保存原始响应、URL、时间和SHA，均为匿名GET，无Cookie或Authorization。另保存了5份页面响应和5份公开脚本。

| 查询型号 | 官方返回 |
|---|---|
| ILME-FX6V | 6.01，条目00002963，BODYDATA.DAT |
| ILME-FX3 | 7.02，条目00003048，BODYDATA.DAT；另有00003047升级说明，后者不是第二份固件包 |
| ILME-FX5、ILME-FX5B | 各两种接口查询均Data为空；型号登记已另行确认 |
| MPC-3628 | VENICE 2 5.00，条目00003066，指向已知V500 ZIP |
| MPC-3610 | 旧VENICE 6.10／AXS-R7 6.0组合包，条目00003067 |

空响应中没有 `totalRecords` 字段，不将其改写为服务器明确返回的数值0。负结论仅覆盖这组型号、分类、接口和观察日期，不扩大为全球、私有维修渠道或今后版本都没有固件。

## 旧 VENICE 与 AXS-R7 组合包的有限核对

中国目录实际给出一个旧组合包URL。范围读取的服务器响应声明总长231,304,333B；ZIP中央目录有13项，主要为VENICE 6.10、AXS-R7 6.0固件、校验文本和文档，未列单独的EXE／DLL／SO等升级程序。没有提取或阅读PDF，也未据文件名排除固件内可能存在的加载器。

最初前缀与尾部分段返回了不同ETag，整包身份一致性未建立。以尾部ETag请求成员头时得到412，原样保留；改用已观察到的前缀ETag做有限复核后，AXS-R7成员返回206且ETag相符，VENICE成员仍返回412。没有移除一致性条件、拼接完整归档或声称CRC／整包身份已经通过。

AXS-R7取得3,996B有效载荷前缀，其ZIP本地头的名称、大小和声明CRC与目录字段相符；这是局部元数据对应，不是完整成员CRC验证。前16B为 `000001354158532d5237000000000000`，未据此指定密码算法。

为检验是否可复用现成解析器，实际取得 [fwtool 固定提交](https://github.com/ma1co/fwtool.py/tree/cdba742b73eed5981480c326aeb30033aabf0223)的源码归档，只读取README与 `fwtool/sony/msfirm.py`。该版本的 `isMsFirm` 要求128B头中间88B全为0；本次AXS-R7头不满足。因此这一具体解析器入口会被结构条件排除，不能仅凭扩展名或产品年代套用。没有导入该源码、尝试密钥、调用解密或搜索签名私钥；也没有宣称所有工具都不支持它。

## 完整目标与验证范围

此次得到的是新的可复核目录路径、经过正对照的FX5空响应，以及一个解析候选的反例。完整私有供体和修改整包准入条件没有因此满足。已有原厂签名验证及修改失败结果按摘要复核，未重跑旧RSA试验；上一阶段37份封存文件一致。

[验证回执](verification-receipt.json)保留原九项要求：完整FX5私有菜单供体、完整VENICE ISP／传感器校准、真实RAM／DMM、CMOS RAW、专业UI与MAIN录像、精确修改固件、经典7.02修改包准入、正常启动与独立恢复、实际刷写前停止。本轮没有将FX6、AXS-R7、公开LUT、元数据或局部模拟替换成完成目标。

原生目标回读为active、未完成。没有下载上述机身固件的完整新副本，没有执行Sony程序、相机／USB／手机／相机IPC／cache或TLB操作，没有修改另一owner文件或运行其工具。

## 复核入口

- [页面与跳转捕获](page-capture.json)、[页面脚本](script-capture.json)、[全站脚本](global-script-capture.json)
- [FX6正对照](china-controls.json)、[全站与型号登记](global-catalog-queries.json)、[注册路径复核](registered-target-queries.json)
- [远端ZIP目录](combo-zip-inspection.json)、[首轮一致性停止](combo-member-prefixes.json)、[另一已观察ETag复核](combo-member-prefixes-prefix-etag.json)
- [固定格式源码](fwtool-source-capture.json)、[独立核查脚本](audit_catalog.py)、[验证回执](verification-receipt.json)
