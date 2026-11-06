# 第四次唯一窗口：同一请求的 CAP 入口与 AP 返回闭合

原始证据为 [`runs/ap-ro-8548d224/`](runs/ap-ro-8548d224/) 内 `command.json`、`source-sha256.json`、`readonly-observation.json`、`serial.log`、恢复样本和 [`receipt.json`](runs/ap-ro-8548d224/receipt.json)。运行源码快照及当前 18 项 host 测试输入 SHA 分别是 runner `73afe6576ad8207f33551f7581e70d64b41101894b361cc0abd6434f66081761`、probe `7da87fbb920bfa6a9516421d1224813056ff991a2c950552c4ccdadc662bbade`、identity `d164c95a14e0d906083e6bbbd05facb4827cc1d4a59dbfc784830ebc2cd6de68`、`host-tests.json` `c8f1e9c98f77f4296913999cb988854dd65f57f1ace6d335a4fb581191c57847`。执行前固定 FX3 完整 `audit.py` 为 `PASS_STATIC_HOST_ONLY_NOT_RUN`，仅宿主 argv 索引 20/31 是私有串口和同一三入口 CPIO 路径；零键、无平台/客体原件修改。

实际 53.623592 秒：第一停顿 QMP `debug` 与 GDB `T05thread:01;` 同时成立，当前 vCPU01 的 PC `0x7f7c1fa730` 对应 CAPID 原 VA `0x1e730`/指令 `ff8301d1`。第二停顿同一 vCPU01 的 PC `0x7ecf6ae7a0` 对应 FX6 AP 原 VA `0x20ef7a0`/`cbz w0` 原指令 `e0000034`；两次 `c` 均收到独立传输 ACK。当前 vCPU 读取的 CAP 与 AP ELF 头、完整 PHDR 和各四处原机器字都匹配固定输入；AP 映射来自本轮同 TID 的原 `dladdr` profile，CAP 映射来自本轮完整 early maps，不使用历史 ASLR。原帧指针链保存 LR 指向该 AP 返回地址。

本轮原请求指针两处同为 `0x7f790781c0`，原 10B 同为 `0d202d030a0001800000`，同一客体 TID770/TLS `0x7ebd159740`。只在这些身份门闭合后读到 **CAPID `model_initialized=0`、`model_process_owner=0`**；AP 同一调用返回 `w0=0xfffffc03`，有符号 `-1021`，原 `cbz w0` 不取零分支，因此断言条件成立。证据是原 CPU 寄存器/内存和只读宿主日志的同调用交叉，不代表 CAPID 服务协议已实现或 FX6 系统启动。

正常收尾：`stop=same_call_return_captured`，`host_error=null`；唯一残余 AP `Z1` 的 `z1` 回复 `OK`、残余集合空，API16 软件 observer 经客体 ack 恢复到原 16B，QEMU `exit=0`/reap、双锁 free、所有固定输入 SHA 前后相同。串口 2,227,102B SHA `b2d6f86f7b5ce81017c7dd9a7125128d4f8cdb35d85985aa18d990d48f5bfde2`。没有方向键或新增 MPR 断点。本轮窗口已经消耗。

**仍未证明**：FX6 AP 的 `mpr::Init` 实际 PLT/GOT 绑定、传入的结构字段及返回值；CAPID model=0 的初始化调用链或它与 MPR 的因果关系；FX6 资源、菜单、CP/AV 或硬件行为。下一 host-only 阶段须从原 AP 指令定位 `mpr::Init` 的最少入口/返回断点并逐门验证动态 AP 映射、调用者与参数；在新授权前不运行 VM，不用 `-1021` 猜造服务成功。
