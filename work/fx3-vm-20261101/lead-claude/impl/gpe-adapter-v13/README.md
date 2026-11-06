# fx3-gpe-observe-v13 adapter

本目录已生成 `fx3-gpe-observe-v13.so`，`python3 build_and_test.py` 退出 0，交叉编译与宿主 ASan/UBSan 测试通过。没有修改 runtime、候选 CPIO、STATE 或启动 QEMU；下一步由运行链工人集成并采集真实菜单请求。宿主通过不代表 guest、菜单或 LCD 验收。

## 复核入口

```sh
cd /Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-claude/impl/gpe-adapter-v13
python3 build_and_test.py
```

- `fx3-gpe-observe-v13.c`：从只读 v12 复制后修改的完整拦截库。
- `fx3-gpe-backend.{c,h}`：后端的本地冻结副本（与兄弟目录源相同，哈希在 build json）。
- `adapter.inc`、`make_source.py`：适配片段及来源重建脚本；常规 build 不执行重建、不依赖兄弟目录改变。
- `compat/string.h`：只有 memcpy/memset 声明；v12 的 `-nostdlib` Zig 环境没有 libc headers，实际符号仍链接 v12 guest libc，不提供替代实现。
- `fx3-gpe-observe-v13-build.json`：UTC、全部输入 SHA256、完整交叉/宿主参数、退出码、输出 SHA256、`file` 类型。
- `build/test.json` 与 `build/host-test.log`：宿主运行退出码、完整 marker、sanitizer 回执。

编译沿用 v12 `aarch64-linux-gnu.2.25 -nostdlib -shared -fPIC -O2 -mno-outline-atomics -Wl,--no-undefined` 和同一 libc/libdl/libpthread/loader。只增加后端翻译单元、声明头路径和 v13 SONAME；Zig global/local cache 均设置到本目录 `zig-cache/`。主项目经核验为非 Git 目录，未做 Git 操作。工具参数参考 [Clang ASan](https://clang.llvm.org/docs/AddressSanitizer.html) 和 [UBSan](https://clang.llvm.org/docs/UndefinedBehaviorSanitizer.html)，2026-11-01 查阅；macOS 禁用不支持的 LeakSanitizer，ASan/UBSan 保持 halt-on-error，宿主用 `-Wall -Wextra -Werror`。

## 保留项与 v12 差异

五个绑定仍为 init `0xc1d0`、Gperm::Init `0x9ae8`、FillRect `0xc30c`、BitBlit `0xcf2c`、Flush `0xc760`，名字/符号值/GOT 校验、三个 worker 的16B原指令校验、setup `0xdb74`、Application_System_Init trampoline、BT error 透传、原 GetInstance/Main/FIFO 均保留。原始来源 v12 SHA256 为 `752f9c22f90d220cd278d4a92a83f8a4f8e9f7cb2fa625d033c3535085274f8d`。

| 项目 | v12 | v13 |
|---|---|---|
| extent | 固定545 | 仍然唯一 ref `{0x545,1}`，base `0x43feb5000`，bytes `0x140000`；generation1只是本次命令局部标签，不是实证分配代次 |
| 可写区 | payload 从 `0x43feb5100` 起 | 同样排除前0x100B头；所有源/目标行必须完整在 payload 至 `0x43fff5000` 内，其他地址返回5，reason=UNSUPPORTED，零像素写入 |
| fill | uniform 同分量覆写 | 后端 fmt0/1、selector0/alpha255，支持不同通道、x/y/stride、padding保留 |
| blit | 全部拒绝 | 后端同fmt0/1快路径，等尺寸、无转换/旋转/特殊flags、scale0或1、完整clip门禁；重叠拒绝，不猜memmove方向 |
| Flush门禁 | 先成功fill，无永久失败，全零24B | 保留先成功绘制和永久失败门禁（成功blit也计入fills_done）；允许async/callback/argument，padding1..7仍须零；未开放空批Flush |
| 完成 | fill不发送；仅Flush4B0 | 成功每命令按async处理，callback先于同步4B0；async且无callback无完成；source0不发同步回复，与v12兼容 |
| 失败 | 原Main处理返回5 | 所有后端错误映射返回5，仅由原Main发送非零失败状态；adapter不自行再发错误，避免重复 |
| 日志 | request原始hex最多64、每fill日志 | 紧凑字段最多200，后续按op计数及2的幂汇总；不输出原始参数全文 |

v13 后端 context 每命令初始化、只注册545并提交一条命令，传给后端的执行副本将 completion fields 清零并置async；由 adapter 在后端返回、内存屏障、extent后验与munmap之后完成。这样不依赖后端64批次上限，不把后端内部 enum 直接发送给 Sony。物理映射覆盖整个已知545 extent，但只有后端预检通过的 payload 行会写；外部地址不 mmap。每次命令前、中、后读取 v12 同样的 `/proc/udm/dmm_extents` 条件，不调用可能分配/映射的 GetDmmMemInfo。

callback 使用原审计16B `{u32 sequence,u32 zero,u64 argument}`，调用前检查 `/proc/self/maps` 包含4B对齐可执行地址；CPU写入先于回调，回调先于4B同步status。本版在现有FIFO worker内直接调用，不复用原CMF CallbackFifo延后调度；参数、顺序、单次调用由宿主证明，guest回调时机/可重入性与原生队列等价性未证实。持有 adapter 的 try-lock，重入请求返回5而不重入同一状态。既有主FIFO仍是正常命令串行来源。

后验extent消失、munmap或完成transport失败发生在成功像素写入之后，返回5并锁住后续Flush，不承诺回滚；这与事前拒绝的零写入保证不同。固定extent轮询没有真正DMM pin/unpin，因此不宣称并发释放安全或动态生命周期已解决。

## 给运行链工人的集成步骤

1. 独立复跑本目录 build，核对 build json 中 SHA256 和 `ELF 64-bit LSB shared object, ARM aarch64`；不要覆盖只读 v12。
2. 在新的候选 CPIO 内，把**成员名 `simulation/fx3-gpe-observe-v7.so`** 的内容替换为本目录 `fx3-gpe-observe-v13.so`。当前 candidate60/70 构建链已沿用该旧成员名装入v12，保留成员名可以沿用启动脚本路径。不要同时 preload 两个版本。
3. 保留 `LD_PRELOAD` 中的 `/simulation/fx3-gpe-observe-v7.so`、现有其他库顺序及 `LD_LIBRARY_PATH=/simulation:/usr/lib:/lib`。v13不新增开关；原capid/VDF等环境变量照旧。库需要可读 `/proc/self/mem`、`/proc/udm/dmm_extents`、callback时的 `/proc/self/maps` 和可读写 `/dev/mem`。
4. 按运行链既有方法更新CPIO哈希、DTB initrd-end及候选说明，单独锁定运行链后启动；本工人未执行这些步骤。必需日志应使用 `FX3_GPE_BOUND ... adapter=v13`、`FX3_GPE_CMD`，不再依赖 `FX3_GPE_UNIFORM_DONE/FLUSH/REJECT` 或 `FX3_GPE_REQUEST`。
5. 先统计真实fmt/flags/地址命中；对result0另做独立物理面readback，对同步/callback检查无重复完成和等待者退出。若遇到unknown地址或非支持格式，按拒绝回执继续审计，不能扩大extent或补造完成。

## 新 marker

`FX3_GPE_CMD op=FillRect|BitBlit|Flush seq= async= fmt= w= h= dst_phys= src_phys= flags= result= reason= read=`。

前200条（所有三个op合计）逐条输出。`dst_phys/src_phys` 是原参数中的完整64位基址，不是加坐标后的首像素；Flush几何/地址为0。fill flags为 `selector<<8|alpha`；blit flags低48位为115..120六字节，48..55位selector，56..63位conversion，alpha和rotation仍由后端验证但不包含在flags槽。`result` 为返回原Main的0/5；`reason` 为本地后端enum：0 OK、1 INVALID、2 UNSUPPORTED、3 BOUNDS、4 STALE、5 BUSY、6 CAPACITY、7 OVERLAP、8 DELIVERY；不是Sony状态码。`read=0` 时其余字段置0，不能当作已读参数。

200条后仅在该op累计条数为2的幂时输出 `FX3_GPE_CMD_SUMMARY op= total= ok= unsupported= seen=`。unsupported包含该op全部拒绝/失败而不限reason2；计数持续更新，不随日志抑制丢弃。汇总不是结束快照：短运行在最后一次2幂之后的尾数尚无输出，长运行可用最后汇总作为下界。原绑定/APP/BT类marker保留。

## 宿主覆盖与未证实项

宿主编译真实v13 worker、extent文本解析与本地后端；只用桩代替pread/open/read/mmap/munmap/日志、native SendDrawComp，以及不可在宿主调用的绑定资源和指令cache操作。覆盖fmt0/1非uniform fill、行padding、两格式有图案blit、callback16B、callback→sync4B0、async无sync、Flush callback、原Main失败4B5唯一回复模拟、无先前绘制/粘滞失败Flush、545外源/目标/头部/末行越界/非活跃extent零写入、重叠/不支持flags/无效callback/读取与映射失败、1100命令中200逐条+3汇总。ASan/UBSan没有诊断，回执退出0。

未证实：guest绑定与权限实际成功、原native函数bool ABI在新路径上的动态效果、真实菜单op分布、异步callback调度与重入等价性、allocator pin、动态DMM generation、partial clip/alpha混合/格式转换/format2..4、opcode2/3、字形/图标栅格、LCD提交与可见菜单。不得把本版本当作菜单修复完成或任何真机写入授权。

本次共享库 SHA256：`4e84b5e0fe5a3c2b3b3e2d8dd2a63a26b80c0efacb56dc4b1110ab34f7c61903`。
