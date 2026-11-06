# FX3 正确AP配置绑定与首次上机准备

2026-10-27。**已在官方更新包中找到正确的 `/setting/DmmCfg.bin`：603个单位、目标20个全匹配，目标各引用1个extent，全文件最多8个。** 这补上阶段128的配置来源缺口；不是用户机身文件、当前分配或硬件主录验收。

用户追问何时能试刷后，本轮将准备重点明确为 [首次上机流程及刷写放行条件](DEVICE_TRIAL_PLAN.md)，并完成Mac缓存采集工具的离线验证。当前没有可安全试刷包，备份、独立救援和真实编码仍未验收，无法给出可靠刷写日期。

## 正确文件的来源

- 原启动 `insmod_drv2` 先选 `/setting/DmmCfg.bin`，不存在才回退到 `/setting/DmmConfig.bin`；随后作为 `DmmConfig=` 参数装载dmm.ko。
- 原fstab将nflasha2挂到 `/setting`、nflasha8挂到 `/cp`。阶段128提取的是后者的43320字节CP配置；本轮选的是更新包成员 `0800_appli/setting/DmmCfg.bin`。
- 本轮AP文件66796字节，CRC32 `f5d46b2d` 与官方appli.sum一致，SHA256 `48c90ca08ae8174d376bf8cbb454a5544e3d024c317e5136fb31d4fb78572bb1`。源FDAT全量SHA、所选tar头校验/类型/名称/长度、启动文件所在官方分区SHA均核对；只读解析，不挂载或运行原脚本。
- AP版本串 `for ilc32g12m-ipsxmp     2025/06/20 15:43:19`。有界解析恰好消费66796字节：1组根记录、290组规则、603个单位。布局来自同包原初始化代码，宿主解析未冒充完整原解析器执行。

## 参数链现在能对应到哪里

阶段126原MPR模式21/25/31/32的7/10/13/19条映射，共49行、20个去重单位，全部在此AP文件中找到且各引用1个extent。本轮记录原MPR行、AP单位偏移、extent类型及候选规则行；没有替这些规则选择当前运行分支、物理地址或真实尺寸。

这为未修改的官方AP文件范围补上块数依据，与MPR保守max8一致。阶段128所见通用长度函数支持1～12块仍成立；机身实际加载哈希、首选/回退文件存在性、WBI缓存及运行时单位维护尚未验证，因此不据此放行设备调用或扩大到任意配置。

离线配置检查器只接受这份固定官方AP身份；CP文件、改字节文件、截断、短头和追加数据均拒绝。6组输入检查通过，没有新增原函数/内核执行。首轮结果保留；正式源将共享卷核验的导入写明，另存复核结果，避免模块同名导入含糊。

## 上机准备的范围

[Mac缓存采集器](mac_cached_usb_inventory.py) 的自测验证Sony VID过滤、父子索引/接口属性保留、序列号/私有属性排除及畸形输入拒绝。测试时把宿主查询函数替换为必然报错，确保自测没有调用ioreg、diskutil或相机。没有实际运行 `--query-mac-cache`；当前授权仍仅历史Windows缓存PnP。

脚本准备完不代表USB请求、认证、健康备份或RAM候选已可部署。阶段75后端/117前端保持guest限定；16项要求状态及权限保持。阶段129文件只作基线与准备，不是刷写包。

- [正式配置结果](run-explicit-shared-volume-check-20261027/AP-config-results.json) · [检查器](ap_config_audit.py)
- [官方提取回执](input-receipt.json) · [完整AP配置解析](AP-DmmCfg-decoded.json)
- [Mac缓存工具自测](mac-cache-offline-tests.json) · [首次上机计划](DEVICE_TRIAL_PLAN.md)
- [诊断约束](diagnostic-contract.json) · [来源范围](source-and-scope-audit.json) · [封存复核](completed-evidence-review.json)
