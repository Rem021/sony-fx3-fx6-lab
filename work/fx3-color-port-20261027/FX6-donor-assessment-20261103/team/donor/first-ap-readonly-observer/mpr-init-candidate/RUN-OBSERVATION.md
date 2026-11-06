# FX6 AP → 固定 FX3 MPR：唯一只读运行回执

**实测结论**：原 FX6 AP 的 `mpr::Init` PLT 调用在固定 FX3 `libmpr.so` 中完成动态绑定；同一 AP 调用从原 `0x212f7b8` 到 `0x212f7bc` 返回 `w0=3`。这是软件拒绝，不是 MPR 初始化成功。GOT 在调用前仍指向 lazy resolver，故本轮没有安装 MPR 入口或 CAPID 入口断点；入口内部路径与 CAPID 是否执行均未动态捕获。原 FX3 代码在 `0xb6870` 将 FX6 记录 `+0x1d0` 的回调指针低 32 位当 count 读取，`0xe3fb3de0 > 4` 与原 `0xb6874/0xb6878` 的保护分支和返回 3 相符，属**原指令加实测参数的静态因果推断**，不是分支轨迹。

## 固定输入与四次停顿

原始回执：[receipt.json](runs/mpr-ro-b22ccc48/receipt.json)、[mpr-observation.json](runs/mpr-ro-b22ccc48/mpr-observation.json)、[source-sha256.json](runs/mpr-ro-b22ccc48/source-sha256.json)。JSON 的 SHA256 分别为 `cc2dcc056fecb556193610e2716062d462b6cb5d88cad2775113287046ad9e19`、`fa8e834e999aafb573118ee34de89b1d7b38111fc13ef1c7122ddef774ef31e2`。FX6 IM `87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec`，FX6 AP `a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067`，固定 FX3 MPR `9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c`。冻结候选 CPIO `bb618bd24f0b504edb14820da4d8204c4b1517cc225e4633eb43f5884f3fff02`。

| 停顿 | 当前 CPU 原字与身份 | 数据 |
|---|---|---|
| IM dispatch | vCPU02；`PC=VA 0x406284`，fileoff `0x6284`，字 `e8feff97`；IM ELF/PHDR/原码核验 | 记录 `0x7f94dcf670`，四字 `20000004,1,ffffff9f,83`；自然路径名 `appFw.so`、入口 `Application_System_Init`；TLS `0x7f62fff740` |
| 同记录 dlsym 返回 | vCPU02；`PC=VA 0x405f10`，原字 `f40300aa`；同 IM TLS | `x0=0x7ee2a83044`，以 AP 原入口 VA `0xc0b044` 得 bias `0x7ee1e78000`；当前 CPU AP ELF/PHDR/代码均匹配 |
| AP 调用前 | vCPU02；`PC=0x7ee3fa77b8`，AP VA/fileoff `0x212f7b8`，BL 原字 `429fa797`；AP 身份复核 | `x0=0x7ed5e763b0`、FP `0x7ed5e76390`、TLS `0x7ed5e77740`；完整 `0x290` 输入 SHA `585d8918da368cec6ef689aa3c14dc3306311ab6661c0bffc9a02e1685430cf1`；`+0x1d0` 回调 `0x7ee3fb3de0`、`+0x268` count `2`、`+0x28a` u16 `1440`；GOT `0x7ee4d69368` 原值 `0x7ee298edd0`，未证明 MPR bias |
| 同 AP 调用返回 | vCPU02；`PC=0x7ee3fa77bc`，AP VA/fileoff `0x212f7bc`，原字 `f35341a9`；同 AP TLS/FP | `w0=3`；GOT 后值 `0x7eed20d844` = 固定 MPR `Init` VA `0xb6844` + bias `0x7eed157000`；当前 CPU 对该 bias 的 MPR ELF 头、280B PHDR 和五个原代码字核验通过 |

IM 两停顿同 TLS；AP 两停顿另一个同 TLS。vCPU02 仅为虚拟 CPU 编号，**不把 IM 与 AP 说成同 Linux 线程**。AP `+0x1f2` 被固定 FX3 代码读取的原 u16 是 `0xe3fa=58362`，属于 FX6 布局错位字节；不能把它与原 FX6 `+0x28a=1440` 混淆，也不能据此选定实际 writer 模式。

## 正常收尾及剩余门

获准的单次窗口 `mpr-ro-b22ccc48` 用时 29.235 秒，零按键、四个 `c` 均获 ACK、QMP debug 与停顿交叉记录；`stop=mpr_same_call_return_captured`、`host_error=null`。残余 `Z1` 的 `z1` 回复 `OK` 且集合空，API16 经客体确认恢复原 16B，QEMU exit=0 并 reap；PID 98718/98715 在报告复核时均不存在，双锁 free，所有固定输入 SHA 前后相同。串口 1,904,929B，SHA256 `011ba0bb9fb048a84428d4a732adeec953e348a3cd5ec65b4e4a3be9a99febd2`。

观察器源码快照与获准输入一致：`observer-mpr_probe.py` SHA `ad6a5f8df3e6e77a3cde1d129fa515090e95b74a581708e4c11e38c208e86d96`，`observer-run_mpr_once.py` SHA `37033deb235351937666eb960c177076f982b321e04204c10694337489668f7b`。六项 host 测试和父目录十八项身份测试是运行前静态门，不替代四条真实 GDB record。

**下一最小工程边**：仅离线建立拒绝式 `FX6 0x290 → FX3 0x1f8` 字段/回调合同，先解决 count、槽位、事件回调尺寸和 u16 模式选择；目前 `Init` 只解释到首拒绝。不能以这次返回 3 推出 MPR/CAPID/菜单、CP/AV、像素或相机功能结果；本窗口已消耗，不自动重跑。
