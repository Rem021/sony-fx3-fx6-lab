# FX3 接口申请子步骤日志与04号诊断候选

2026-10-28。**已编译并通过34项当前本地检查；04号未授权未执行。** 03号真实root身份/ACK/capture已通过，但接口申请总阶段返回NoResources；随后全部同机缓存驱动恢复且用户屏幕正常。原始UNKNOWN及01/02/03占用记录保留，尚无可用接口、主录或救砖证明。

## 本候选只增加可定位的结果记录

[源码还原复核](provider-trace-derivation.json) 对新增包装逐项逆变换，可精确还原166版原生提供者全文。设备调用表达式、参数、顺序、配置选择及重试政策均不变；只在原返回值交给原判断前，把固定子步骤ID和原始32位码追加到现有结果事件数组。IOReturn和HRESULT宽度有编译期检查，不截断更宽类型。共享ABI仍3、入口schema仍2、事件容量仍64；最保守总事件61，不挤占后置40次缓存快照预算。

[子步骤表](claim-substep-map.json)：101为条件设备open，102迭代接口，103创建接口plugin，104 QueryInterface650，105/106/107为接口号/备用设置/端点数读取，108接口open，109按pipe1/2顺序查询端点属性。每个原API仍只调用原来次数；不设置配置、不重试。结果跟随原native SHA回执和独立PID身份核对，不依赖可能被管理员中继丢弃的stderr。

[3项同源C内存检查](claim-trace-memory-tests.json) 直接运行原生提供者中的同一日志函数，核对负错误码/顺序、64项容量及相邻canary、61项预算。其程序不含IOKit。[13项内置复制](internal-stage-tests.json)、[13项启动](hardened-entry-tests.json)、[5项观察](recorded-observer-tests.json) 通过，共34项当前检查；9个有记录fixture的PID已逐一核对缺席。166的6项跨用户内核身份检查及167的真实root确认按源码一致性复用，不充作新04实机验收。新原生helper仅编译未运行，管理员源码只解析。

## 待确认的单次04方案

[完整方案](candidate-plan.json) · [固定运行包](release-bundle.json) · [源代码/运行复核](local-source-and-runtime-review.json)。

- 编号：fx3-702-msc-owner-20261028-04。
- 运行包SHA-256：0bfe5210a392dd0b57752e8e5d67e23f2597a34f24e7609b8bad37b80dd0ca72。
- 原生helper SHA-256：661e679e725a6b5cc9431c63b747fb1d15412b05856663461bb856c232b00651。
- 目标：经典ILME-FX3、用户确认固件7.02，054C:0DA1、location0x02100000。
- 用户目录：/private/tmp/fx3-702-msc-owner-20261028-04/，0700；源程序0500、共享帧0600。
- root目录：/private/var/root/fx3-owner-trials/fx3-702-msc-owner-20261028-04/，0700、root helper0500。

确认后，先重验相机卷已手动推出、仍开机连接MSC、唯一缓存身份和固定SHA，再只执行一次原生USB接管与归还诊断。可能短暂断开存储连接，必要的原生管理员验证由用户完成。只创建上述本机程序和不可重用记录，不增加完全磁盘访问、驱动或常驻服务。

不进行Sony认证/服务、不读卡或机身文件，不读写模块、WBI、设置或固件，不修改配置或备用设置，不自动卸载、不主动调用USB reset、不强杀或重试。任何启动失败也消耗04；调用阻塞时保留同一worker和UNKNOWN。完整驱动缓存可能晚于接口关闭出现，独立缓存后查单独记录，不覆盖原回执，也不把缓存/屏幕正常当作完整相机功能或救砖验收。

03仅授权一次且已消耗，不能覆盖04。新04现authorized=false、released=false，没有创建实际任务目录或占用凭据。目标1080/29.97 HEVC42010约16Mbps主录、完整备份/恢复回读、独立救援、长录、冷启动及音画同步继续未验，持久刷写关闭。
