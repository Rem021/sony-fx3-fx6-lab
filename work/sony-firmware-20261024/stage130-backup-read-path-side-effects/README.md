# FX3 Mac缓存盘点与备份读路径审计

2026-10-27。用户明确回复“可以，仅查 Mac USB 缓存”后，已完成两次限定的系统缓存读取：**1台Sony ILME-FX3，VID 054C / PID 0DA1；接口0为08/06/50，缓存中有IOUSBMassStorageDriver。** 未打开USB接口、发送相机命令、认证/切模式、改变驱动、读取素材/机身文件、上传模块或刷写。

## 已完成的Mac缓存关联

原阶段129已封存的采集器读取IOUSB树，得到1个Sony候选，未包含接口子节点。第二次只读IOService中的USB设备子树，并复用同一白名单过滤器，补到IOUSBHostInterface及其驱动后代。

IOService结果有4条带Sony VID/PID的记录，其中3条是接口/nub继承属性。对已保存的去敏记录按树索引路径归并后，只有1个IOUSBHostDevice根；不是4台相机。接口0是Mass Storage/SCSI transparent/Bulk-Only，和此前Windows记录的054C/0DA1一致。

序列号、盘符/卷名及其它私有属性不落盘，原始IORegistry内容只在内存处理。缓存中已有AppleUSBHostDeviceUserClient等节点不说明本工具打开过接口，也不证明当前能独占通信。没有安装、卸载、抢占或重置驱动。缓存身份与驱动关联不证明7.02固件文件哈希、认证、机身健康备份或恢复能力。

本次新授权只增加Mac系统缓存元数据范围。Windows/UU仍按此前要求不操作；主动USB/SCSI/PTP/vendor、认证、相机文件、模块、WBI和持久写入仍未授权。

## 备份“读”接口的新限制

对固定SHA的FX3原libJiritsu.so做静态复核，并执行7组、8个原分支片段，发现：

- GET_FILE2的内部kind0/selector3路径，在共享对象有待处理日志指针/长度的声明条件下，会准备flags0x441的文件打开，再写待处理日志、fsync、close及sync，然后才进入读取。目标是日志路径，不是本轮证明写了固件；这些服务均未执行。
- 0x441按[Linux 4.9打开标志](https://github.com/torvalds/linux/blob/v4.9/include/uapi/asm-generic/fcntl.h)是O_WRONLY/CREATE/APPEND。原分支准备了这组参数，但没有执行构造器、打开或写入。不能因命令名含GET就保证整个命令无持久副作用。
- 原路径早先调用sys_mount，源是/dev/nflasha6、目标/tmp/jiritsu，输入flags0xc0ed0490没有[MS_RDONLY位](https://github.com/torvalds/linux/blob/v4.9/include/uapi/linux/fs.h)。实际helper可能复用现有挂载；本轮不声称发生真实挂载或写盘。
- 旧候选参数00/ff/00在所测片段跳过上述日志分支，但还会经过挂载/路径处理、stat、DMM整文件申请、读取、fsync和close。没有因此放行。
- 空全局根指针没有先经过原空值守卫；首轮脚本曾误把它当普通拒绝输入并出现未映射读。源/失败结果保留，复核将该输入止于原解引用前，观察器停点不冒充固件防护或成功错误返回。

另外，get_access_filename会按/tmp/jiritsu前缀和原格式串处理路径。简单发送 `/setting/DmmCfg.bin` 不能直接证明解析为目标AP文件；既有保守codec也拒绝该路径。旧codec仅允许65536字节主机数据，官方AP文件66796字节超出1260字节；其读请求没有相机端文件长度上限。**当前适配器不能作为这份AP配置的现成安全备份程序。** 未扩路径策略、未使用路径穿越或发送新请求。

[PMCA固定版本的readFile](https://github.com/ma1co/Sony-PMCA-RE/blob/a82f5baaa8e9c3d9f28f94699e860fb2e48cc8e0/pmca/usb/sony.py#L916-L934)使用另一pFunc=ff01、cmd2家族，不等同于已定位的Jiritsu AdjustControl路径；它在本机型上的路由、可达性、边界和副作用仍未核验。

## 对上机流程的影响

[备份步骤补充约束](BACKUP_READ_REVIEW.md)续接阶段129的首次上机计划。步骤0已得到Mac缓存证据；步骤1主动诊断/步骤2健康备份仍不放行，更未达到临时修改或刷写。下一步优先核对可用于备份的读文件家族及原接收器/退出语义，不再把旧读命令名、主机分片或局部零返回当成安全证明。

目标仍为经典FX3 7.02的1920×1080、30000/1001、HEVC42010约16Mbps MAIN，精确30.000另列。16项要求状态保持；当前guest限定前后端未变；实际文件、音画/长录/冷启动、同机备份、恢复回读和独立救援均未验收。

- [Mac缓存归并结果](mac-cache-association-review.json) · [IOUSB回执](mac-cache-20261027T183151Z/sanitized-cache-receipt.json)
- [IOService回执](mac-service-cache-20261027T1834Z/sanitized-service-cache-receipt.json) · [补查脚本](mac_usb_service_cache.py)
- [正式分支结果](run-explicit-null-root-boundary-20261027/read-path-results.json) · [原代码与来源](source-and-scope-audit.json)
- [授权增量](authorization-change.json) · [诊断约束](diagnostic-contract.json) · [封存复核](completed-evidence-review.json)
