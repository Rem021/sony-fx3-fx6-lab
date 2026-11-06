# r30 观察合同

观察只输出证据，返回值不得作为 ready、健康、点击、重发或清理许可。原调用异常与原准入结果保留；诊断自身异常仅计入固定错误计数。对原控制表达式的观察函数返回原值对象，原 BoolOp 决定是否继续求值。

`startup-observation.json` 位于真实 runner run目录，schema=`fx3-startup-observation-r30-v1`。正常回收后只尝试一次临时文件替换，最大256KiB；失败或SIGKILL时该文件可能不存在，不能把不存在当作 guest 无调用。普通receipt附记录写入状态，观察不参与健康结果。

| 类别 | 含义 | 不能推断 |
|---|---|---|
| short/wrong_length/missing_export | 原长度/文件门未得到256B输入；错长度可只读同一文件的128B前缀 | QMP空成功等于有效header |
| bad_magic / bad_version | 原返回256B，16Q包含不匹配值 | ring已初始化、guest未绘制 |
| valid_seq0 | 原全局头magic/version有效，序号0 | guest所有私有/offscreen像素不存在 |
| valid_positive | 原全局头序号>0 | 槽/FNV/非全零/ready已通过 |
| qmp_exception | 原QMP调用抛出，保留异常类型、已分配id | 旧文件是本次结果，或可以补发 |
| qmp_error_response / host_read_exception | 原错误响应空返回或原文件读取异常 | 可以弱化错误继续 |

`raw_16Q` 只来自本次已返回header，或本次错长度宿主导出的有限前缀；异常/未取到128B时为null。错长度prefix明确标记diagnostic_only，不是原reader输入。长度与读取前后时间本身也不是guest原子证据。request_id仅当实际transport序号前进时填入，否则null；无新QMP请求。

Marker字段 byte_offset 是原文件绝对字节位置；只匹配静态白名单literal token，不保存完整行或私密环境。`host_first_complete_token_received_ns` 为本次新增bytes在host完成读取后进入观察的时刻；`line_complete_received_ns` 为后续LF已收到的时刻，可为null。跨chunk只拼接最长token−1字节；跨byte流缺口会清空尾巴并计数，不能拼造marker。首次token存在不代表字段/事务完整，原日志保留供独立复核。

Ready共13个命名条件：phaseA_unobserved、replay_input_verified、screen_open_observed、validated_ring_present、screen_quiet_10s、media_branches_exact、media_notifications_exact、native_free_sizes_present、key96_ready、front_full_body、expected_raw_message、last_screen_allowed、nonuniform_pixels。true/false只表示该次原表达式实际求得的结果；`not_evaluated` 表示短路未知，`unknown_type`表示观察器不解释该类型。没有观测时的null/空流表示unknown；求值异常留下evaluation_complete=false，不补写false。qualified只表示原本地phaseA_capture已存在，既不是HTTP实时ready，也不是下一键许可。最后screen时间是原host察觉screen计数变化的点，不是原屏幕事件时刻。

内存只额外保留定长14项marker、token尾巴、header48/ready32/phase8个最近状态变化，以及各流最多32种首次状态、初始/末次。重复读也计数，但不新增变化项。evicted_transitions、first_kind_omitted明确说明丢弃；序列化超限会清空recent数组并报告serialization_omitted_recent，仍保留初始/末次和首次状态，不悄悄伪装完整历史。cleanup阶段独立，首次cleanup像素永不倒填为startup ready。

最终文件≤256KiB，无逐poll fsync/rewrite；异常导致的tmp残件也受同上界。新成本为定长分配/字典操作、对白名单扫描新增chunk、必要时128B宿主文件peek和一次最终写盘；不新增guest写入、暂停、QMP、sleep或轮询。r28原PAGE/server、快照、恢复、20秒和5秒观察合同保持。
