# 人工恢复后的新诊断准入

**同机普通MSC恢复已取得实际缓存证据；追加式重新准入规则和root缓存验证器已实现/编译，尚未接成新的管理员入口。** 本轮没有新root执行、Sony命令、USB请求或真实root journal修改，也没有新上机许可。

## 真实机身证据

用户在265收尾前明确确认机身侧USB-C已拔下，电池供电下界面/菜单正常；之后按已授权的仅缓存范围重新连接MSC。本轮普通用户IORegistry核对到054C:0DA1、ILME-FX3、节点4295963942、位置0x01100000及原物理USB-C锚点4294968654，MassStorage/SCSI/BlockStorage类别恢复。缓存串号只在内存用原隐私key计算HMAC，与262实际MSC帧中的标签一致，原串号和key未存入本轮记录。

[恢复后的同机MSC缓存](recovered-MSC-cache.json)。这证明本次故障后已回到一致机身的普通USB缓存状态；原262仍是历史HELD，不能改判正常STOP/退出，不能外推为固件变砖可救。标签是缓存一致性，不是固件密码学认证。卷未要求推出，本次未把挂载状态计为可接管。

## 追加式规则

保留旧v1 journal的所有字节，新增v2的`MANUALLY_RECOVERED`事件，再在同一flock期间追加绑定新nonce/新grant的OWNED。旧CLEAN不会被伪造，旧UNKNOWN/OWNED不会被删除。普通begin仍拒绝失败尾部；新恢复入口只接受固定的旧owner/observer/nonce/grant、已结束的旧进程身份和新的同机缓存证据。

新的私有回调必须自己读取缓存：两次唯一MSC身份/物理端口核对夹住驱动/IOMedia及内核mount表检查，前后相同且完成用时不超过2秒。源节点必须是固定的新节点，HMAC须匹配原机身，驱动存在、挂载数为0且介质状态明确；安全推出后零IOMedia允许。旧进程仍在、身份不明、缓存过期、错误节点/端口/机身、卷挂载或缺驱动均拒绝。用户保存的JSON/布尔值不能替代该root私有回调。

新nonce和grant必须在整段历史中从未使用。写完恢复事件但未写OWNED就中断时，留下的尾部继续阻止普通或恢复入口，不能自动续接。短写、坏摘要和损坏尾部拒绝，不填补或截断。这个事件仅表示“人工恢复后允许一项新的受控诊断”，不表示旧试验成功、完整健康、救砖或固件写入权限。

旧v1读者会拒绝含v2的文件，保持失败关闭；新版本必须有明确scope后才能使用，不能随意换锁路径绕开它。

## 实现与验证

- [global_guard.c](global_guard.c) / [接口](global_guard.h)：实际追加式文件与进程身份规则。
- [root缓存验证器](native_recovery_cache.c)：仅IORegistry和getmntinfo(MNT_NOWAIT)，无USB user-client/interface、设备请求、介质/卡文件open。缓存身份调用的底层分支已核对仅用IORegistry/端口属性；适配器其余USB方法不在这条路径中。
- [7组主机回归](host-checks.json)：真实普通用户子进程、文件和flock；设备与缓存输入均为人工数据。OWNED/UNKNOWN两种旧尾部均保留原前缀，追加恢复/新owner/UNKNOWN；12种错误缓存、旧owner或observer未结束、历史grant/nonce复用、恢复记录后中断及破损尾部均拒绝。旧264读者对三种v2日志均拒绝且文件不变。
- [原生缓存对象编译与导入符号](native-cache-build.json)：缓存验证器及生产guard均仅编译为对象，未执行。测试程序不链接IOKit，使用ASan/UBSan和-Werror。早期host版本与后续历史许可复用收紧的记录保留在history/、attempt01和attempt02。

## 尚未放行的部分

还需将此接口接到264的管理员入口，在固定许可中绑定恢复证据、旧记录标识、同机HMAC材料、新节点及新范围，并回归完整helper/观察器流程。之后才形成新的单次通信包，说明host journal追加、Sony认证/模式副作用与异常收尾。265的清理授权已消耗，不覆盖这次真实journal写入或新Sony通信；本目录不申请或执行它们。

真正上机前须再次核对当前缓存和卷状态，不能把本轮有时间的缓存快照当作两秒新鲜证据。当前无需用户再验证或进行相机动作，保持MSC即可；尚未发送新的认证、88字节读取、STOP、程序上传或固件写入。原G01至G16及全部首刷条件保留。
