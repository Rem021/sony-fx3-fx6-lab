# 当前 7.02 queue0x376：真实回调层次与仍未识别的收件人

## 旧 `.text+0x3644` 的节点函数是否就是启动切换处理函数

### Takeaway

**不能把旧的 `node+0x10 → blr x3` 命名为 LSI／boot 切换处理函数。** 当前原 `osal_uipc.ko` 的可见公开 API 路径会将该字段设为 OSAL 内部唤醒、进程投递或内核回调包装函数；其中普通阻塞接收甚至不调用显式 `osal_reg_msg_queue_cb`，自己临时挂一个栈节点。真正业务处理可能在被唤醒线程后续代码、用户回调，或节点 `+0x20` 的第二次间接调用。[带原重定位注释的指令](../../evidence/queue-consumer/annotated-pins.txt)；[回调字面量重定位](../../evidence/queue-consumer/callback-provider-relocations.json)

### Cited Findings

本轮只运行宿主自写静态分析，沿用现有 Capstone 5.0.9／pyelftools 0.33 环境，没有执行原固件、原脚本、guest、内核或相机操作。当前 AP ext2 SHA-256 `df0a2cf2ebb0d884605d041a6dcb701092bd36848956855b8d3d7a7164a3a1c5`；卷身份已在写入前核对为 `F9404A58-A1C4-409F-8E78-9A6B7EEB3F7B`。原来源未改。[范围回执](../../evidence/queue-consumer/scope.json)；[源文件指纹](../../evidence/queue-consumer/source-manifest.json)

| 当前原件 | SHA-256 | 地址合同 |
|---|---|---|
| `/kmod/osal_uipc.ko` | `6aa0f5c8c72f5f6cf9aa9c905fc3f3f75b8bea0dfebaf13deb632b0de088eb38` | `.text+offset`；未应用运行时重定位，不是实机 VA |
| `/lib/libosal_uipc.so` | `09ebf5980237fc473077dc844763dcb00cba423f431646e3be7c0ca49ea70ff3` | ELF 链接 VA；不是已观察的运行时基址 |
| `/kmod/liro.ko` | `b4bd80cc614751e0092ee19e89cb90632db580bc01f23f1a1df23544e9b10186` | 模块节内偏移 |
| 当前 `av-cam.bin` | `0cb7e03a59b4ec3d7633664ab0f7a9477892d1aaf442b9db83a7e9a62a49bdaf` | 原始 ORIL 映像文件偏移，以映像起点为0 |

[四份源文件清单](../../evidence/queue-consumer/source-manifest.json)。本轮 13 组原指令片段的原文件偏移、长度、SHA-256 独立记录，便于按字节复核；反汇编没有修改源文件。[片段指纹](../../evidence/queue-consumer/instruction-slices.json)

三类节点的具体构造如下。此表证明原机制，**不声称已经观察到 queue0x376 的某个运行时节点**。[原登记与消费指令](../../evidence/queue-consumer/annotated-pins.txt)

| 节点来源 | `node+0x10` | 实际作用／下一边界 |
|---|---|---|
| 普通 `osal_rcv_msg_tmo` 的阻塞等待 | `.text+0x2910` | 将消息正文地址写入接收者输出槽，`wake_up_process(task)`；接收线程醒来后才可能处理数值0／2／5／6 |
| 内核 `osal_reg_msg_queue_cb`／`osal_reg_sync_msg_queue_cb` | `.text+0x28c0` | 包装函数解除队列锁，取 `node+0x20` 真回调和 `+0x28` 参数，在 `.text+0x28ec blr x2` 调用，再锁回 |
| 用户空间显式注册，经 `/dev/uipc` | `.text+0x15f0` | 包装函数把任务放入所属进程 pending 链并唤醒用户代理线程；用户库读取事件后才调用用户函数 |

**普通阻塞接收的原数据流：** `.text+0x4198` 为原 `osal_rcv_msg_tmo`。当队列当前无可直接取的消息且超时参数非0时，`0x4290` 将 `x2=x29+0x68`，`0x4294` 从字面量 `0x44b0` 取函数指针；该原 `R_AARCH64_ABS64` 重定位明确指向 `.text+0x2910`。`0x42a0/0x42a8` 清零临时节点；`0x42ac` 写 `node+0x19=4`；`0x42b0` 将函数指针写到 `x29+0x68`，亦即 `node+0x10`；`0x42b4` 把接收输出指针 `x22` 写到 `node+0x28`；`0x42bc` 把当前 task 写到 `node+0x20`。`0x42ec` 明确 `node=x29+0x58`，`0x42f0` 将它挂到队列 `+8` 回调链尾。之后才释放锁及 schedule／schedule_timeout。[完整自动登记与唤醒片段](../../evidence/queue-consumer/annotated-pins.txt)；[字面量指纹](../../evidence/queue-consumer/callback-provider-relocations.json)

它的实际唤醒函数只有 `.text+0x2910–0x2938`：`0x2914` 将消息头地址加`0x18`得到正文指针；`0x291c/0x2920` 把它写入 `node+0x28` 指向的输出槽；`0x2924/0x2928` 取 `node+0x20` 当前 task 并调 `wake_up_process`；置w0=0返回。此函数没有读取消息4字节数值，没有 switch 枚举、Backup写入、FAT操作或启动寄存器写入。[原唤醒函数13片段中的blocked_receive_callback](../../evidence/queue-consumer/annotated-pins.txt)

**内核显式回调的原数据流：** `.text+0x4ae0` 保存登记参数 x2=实际回调、x3=参数，`0x4b48` 写至 `node+0x20/+0x28`；`0x4b44/0x4b4c` 通过字面量 `0x4c90` 把 `.text+0x28c0` 写至 `+0x10`。同步版 `.text+0x39d0` 在 `0x3a20/0x3a24` 做同样的存储，字面量为 `0x3ac8`。包装函数 `0x28e4` 从 `node+0x20` 取x2和 `+0x28` 取x1；`0x28e8` 将消息头+0x18作为x0；**真正的下一次间接业务调用为`0x28ec blr x2`**。因此即使恢复出第一层为0x28c0，仍不能跳过节点+0x20的目标识别。[内核两种登记及包装原指令](../../evidence/queue-consumer/annotated-pins.txt)

**用户显式回调的原数据流：** 注册分派器 `.text+0xe90` 读32B用户参数，`0xf04` 从字面量0xfc8取`.text+0x15f0`，`0xf0c` 写`node+0x10`；用户回调写到`node+0x20`，参数写`+0x28`，所属进程上下文写`+0x30`，`+0x19`标志加8。`0xf94/0xfac` 分别调用低层 sync／普通链登记。`0x15f0` 的两条分支均通过`0x1538`投递：后者把节点链接进`process+0x38` pending链，保存消息头，在`0x15b4`对等待代理task调用`wake_up_process`；同步分支还会等待完成。[原用户登记及投递片段](../../evidence/queue-consumer/annotated-pins.txt)

当用户代理读取事件时，内核`0x9e4/0x9ec/0x9f4`将节点`+0x20`回调和`+0x28`参数复制到输出结构，`0xa0c–0xa20`把消息正文转换为该进程映射地址，`0xacc`复制32B到用户。当前用户库在`0x32e8`从结果结构取回调x2和参数x1，`0x32ec`取正文x0，**`0x32f0 blr x2`才进入用户函数**。这证明先前内核`0x3644`并非必然在执行最终收件业务。[内核返回事件／用户代理原指令](../../evidence/queue-consumer/annotated-pins.txt)

### Inferences

- 原 queue walker 的一般语义应改写为“唤醒／交接／包装分派边界”，不能写成“已到启动切换handler入口”。其中`.text+0x2910`是可完全解析的纯唤醒路径；`.text+0x28c0`和`.text+0x15f0`也有明确后继业务边界。[原指令](../../evidence/queue-consumer/annotated-pins.txt)
- 仅搜索`osal_reg_msg_queue_cb`导入者不能穷尽普通收件者，因为阻塞`osal_rcv_msg_tmo`在自身栈上登记节点；这是前轮“登记者可能仅是显式reg API调用者”假设遗漏的一条真实路径。[普通接收原指令](../../evidence/queue-consumer/annotated-pins.txt)

### Gaps

- 仍未恢复queue0x376**实际运行时节点**、它来自哪类登记，以及对应用户线程或内核业务函数。因此不能声称它确定为唤醒0x2910、用户代理0x15f0或内核包装0x28c0之一；三条是由原代码证明的公开构造路径，非某次运行的观测。
- 既不能从间接调用说已切LSI，也不能从普通唤醒路径说命令无效；真正业务在后续线程／回调中可能发生。

## 定向登记导入、LIRO原始映像和模块顺序给出什么新限定

### Takeaway

已把静态搜索从“立即数命中”推进到原重定位、登记包装和LIRO导入向量：当前 AP 的相关kernel模块重定位已列清，当前av-cam的显式登记veneer也已定位。**尚无原证据将queue0x376绑定到av-cam或某一具体模块；LIRO线索不能冒充已找到收件人。**[内核导入审计](../../evidence/queue-consumer/import-audit.json)；[LIRO元数据](../../evidence/queue-consumer/liro-metadata.json)；[av-cam登记调用窗](../../evidence/queue-consumer/avcam-registration-windows.txt)

### Cited Findings

- 当前`liro.ko`的`.rela.init.data+0x380/+0x388/+0x390`分别是`osal_reg_msg_queue_cb`／unreg／sync的`R_AARCH64_ABS64`导入。原装载复制片段`.init.text+0x4b0–0x4c8`把`.init.data`长度`0x698`复制到原映像接口区`+0x48`，故普通登记是API偏移`0x3c8`，sync是`0x3d8`。这条依赖要在LIRO装载复制后才有非零运行时指针，不能只凭未装载向量槽零值断言不会登记。[LIRO元数据／导入记录](../../evidence/queue-consumer/liro-metadata.json)；[装载复制原指令](../../evidence/queue-consumer/annotated-pins.txt)
- 当前`av-cam.bin`原veneer`0x2efec–0x2f000`读取映像头`+0x20`接口指针，再取接口`+0x3c8`并`br x4`；`0x2f014–0x2f028`同样取`+0x3d8`，分别绑定上述两个原登记API。本轮枚举了原始映像对这两个veneer的直接B/BL调用，保留每处登记前原参数设置窗口。[veneer原指令](../../evidence/queue-consumer/avcam-veneers.txt)；[原登记xref](../../evidence/queue-consumer/avcam-api-xrefs.json)；[参数窗口](../../evidence/queue-consumer/avcam-registration-windows.txt)
- 原av-cam`0x3effec`确有32位`0x376`，但它位于连续20B配置记录中，邻接记录为0x375／0x377，后四个w字段为`0x4b00,1,0x80,1`。原读取代码`0x27bca0–0x27bdb4`使用20B步长，取第三字段作分配数量，累加长度和存储指针，生成32B记录；没有在这里调用OSAL登记API。故该命中目前只证明配置记录，不能充queue0x376 callback登记。[原配置字节和xref](../../evidence/queue-consumer/avcam-queue-table.txt)；[原初始化指令](../../evidence/queue-consumer/avcam-generic-initialization.txt)
- 当前 AP 的相关kernel重定位扫描包含LIRO导入表、upm等模块显式登记及OSAL本体低层登记；另对使用send／receive／register API的用户ELF列出原导入，并进一步记录相关高16位ID设置的原指令窗。该审计没有找到可证的queue0x376应用处理目标。[内核重定位](../../evidence/queue-consumer/import-audit.json)；[内核登记参数窗](../../evidence/queue-consumer/registration-windows.txt)；[用户ELF导入](../../evidence/queue-consumer/user-import-audit.json)；[ID参数窗](../../evidence/queue-consumer/high-id-audit.json)

### Inferences

- 真正有用的装载顺序限定只到“LIRO复制向量先于通过该向量调用登记”。本轮没有依靠脚本名称、地址相近或某条已加载模块顺序把0x376强行分给某模块；实际queue0x376登记的时机与来源仍需独立确认。[原复制与veneer](../../evidence/queue-consumer/annotated-pins.txt)；[原veneer](../../evidence/queue-consumer/avcam-veneers.txt)
- av-cam／LIRO内核域、用户AP进程及其他处理器域必须分开。当前审计没有得到把这条请求送往另一处理器或证明其能脱离MAIN运行的原代码链。

### Gaps

- 未穷尽动态生成ID、表驱动收件人、WBI装载状态或普通receive调用的数据源；没有把静态未命中写成“当前固件不存在收件人”。
- `0x3effec`配置记录的全局资源合同不在本轮目标内，未给它添加“LSI”“boot queue”或处理器所有者名称。

## 现在的最小下一目标与恢复结论边界

### Takeaway

这一轮解决了**旧间接点的语义误判风险**，没有解决queue0x376实际业务所有者。下轮应先恢复该队列的真实收件登记／阻塞接收调用及参数来源，再沿对应的第二层边界追0／2／5／6，而不是继续把`.text+0x3644`当最终启动处理地址。[三类节点原证据](../../evidence/queue-consumer/annotated-pins.txt)

### Cited Findings

- 最小可复核的分流点为queue0x376链中的节点`+0x10`和`+0x19`标志、`+0x20/+0x28/+0x30`字段。若来自普通接收栈节点，应逆追以queue0x376调用`osal_rcv_msg_tmo`的原线程；若为内核显式登记，目标转为`node+0x20 → .text+0x28ec`；若为用户显式登记，则逆追原32B登记参数中的用户函数并接`libosal_uipc.so+0x32f0`。[节点构造与真正调用](../../evidence/queue-consumer/annotated-pins.txt)；[重定位类型和目标](../../evidence/queue-consumer/callback-provider-relocations.json)
- 本轮源件和13组片段均保留哈希，输出只在stage183自己的queue-consumer目录；没有生成或传递相机payload，没有设备／管理员／USB／Windows／UU／GUI动作，也没有执行guest。[指纹清单](../../evidence/queue-consumer/source-manifest.json)；[片段指纹](../../evidence/queue-consumer/instruction-slices.json)；[范围回执](../../evidence/queue-consumer/scope.json)

### Inferences

- 当前可给恢复路线增加的是“通用请求队列分派与最终业务消费不同层”的合同；不能增加MAIN损坏后的独立触发能力、持久selector改写成功或实际重启成功回执。
- NOR早启文件选择、USB／MAIN失败可达性由其他研究线分别核对；本轮未借用它们的结论去补queue0x376中间缺失的一跳。

### Gaps

queue0x376的实际登记者／当前节点／真实应用回调和0／2／5／6执行效果仍未确定；Backup0x004b0000的当前机身值也未读取。停点现为上述明确的三类交接边界及待识别收件人，不是启动loader或LSI的实证入口。
