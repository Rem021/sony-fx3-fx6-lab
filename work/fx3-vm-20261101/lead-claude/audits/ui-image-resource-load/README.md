# UI 图像资源加载：主批量图像依赖 LDEC 硬件，当前缺失 provider 最可疑

2026-11-02。**已经确认主批量 `image_*.uxc` 走 `/dev/ldec` 硬件 LZ77 解压；最可能的 VM 断点是 LDEC 设备/provider 没有建立，而不是这些文件没有进入 guest。** 9 份原图像文件与 AP102 v3 CPIO 成员逐项大小、SHA256 一致；原进程还实际映射了三份 `_43` 文件。全部 **51,642 条有效 uxd 图像记录都是 encoding4、资源像素格式0**，原工厂对 encoding4/6 创建 `Lz77Decoder`。但是，**本轮没有实际 `open` 的返回值/errno，也没有具体纹理的 resource ID→decoder→bitmap 身份链，因此“缺 LDEC”仍是 B 强假设，不是已捕获的唯一运行根因**。（A1：libObj `113710–113744、15c6a0–15c700、154c40–154f14`；A2：下文 CPIO 表、serial LF39902/39906/39907；proof `resources、original_libObj、runtime`。）

另有必须保留的例外：`image.uxb` 含 **3 组各277条、共831条内嵌 PNG**，对应 encoding1，原库有 libpng 软件解码分支。`global.xdb` 中没有字面量 `image.uxb` 引用，因此不能宣称这831条本轮都被使用，也不能将“少量图形可见”直接绑定到它们。（A1：文件 `image.uxb` 的表/PNG/IHDR；libObj `113c80–113f10、15c64c–15c698、15f458`；proof `resources.uxb_png_groups、global_xdb_literal_image_uxb_reference`。）

## 复现、输入与边界

在 Mac 项目根运行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python -B work/fx3-vm-20261101/lead-claude/audits/ui-image-resource-load/audit_ui_image_load.py
```

退出0，重建 [ui-image-load-proof.json](ui-image-load-proof.json)。[脚本](audit_ui_image_load.py) 使用既有 capstone/pyelftools/Unicorn，检查外盘 UUID、固定原库/模块 SHA、核验资源与 CPIO 成员、解析保存的纹理直方图，并隔离重放原厂打开失败分支。PASS 表示审计重建和断言成立，**不表示解码或菜单已修复**。脚本的 `--dump VA BYTES` 仅显示 libObj 指令，不重建 proof。

只写本目录三份文件；未启动 QEMU、未访问 QMP、未拿运行锁、未修改 runtime/STATE/固件/Git，也未操作相机。采用 [Capstone 官方 Python API](https://www.capstone-engine.org/lang_python.html) 核对反汇编方法；Sony 私有语义全部取自本地原件，没有借用 FX5 的 ioctl 布局。尤其原 FX3 的目的地址是32bit，不能套用邻机 `u64 dst_phys` 结构。（A1：原 FX3 ldec.ko `.text+870–a54`。）

本文相对路径均以 `work/fx3-vm-20261101/` 为根：

- `AP`：`menu-repair-01/original-uipc/ap-projection/regular-files/`，用户库在 `usr/lib/`，资源在 `usr/share/app/`。
- 原模块：`menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/ldec.ko`。
- `RUN`：`menu-repair-01/runtime/runs/ap102v3observe600-10fbf756/`；日志行号按 **LF、从1开始**，不将 CR 当换行。
- 纹理输入：`menu-repair-01/runtime/ap102v3observe600-10fbf756-graphics102-v1.json`。

用户库 VA 均为 ELF 链接 VA，运行采样需加**该次 libObj 实际加载基址**；`.ko` 地址一律写成节名+offset，不能直接作为运行 VA。A1=原字节/表/重定位及有界分支重放，A2=保存的运行回执，B=推断，M=实施规格，U=未证实。

| 原件 | SHA256 |
|---|---|
| libObj.so | `c4681d209a7fe2ed63752be3b0be89ab7b7ce400679c00068c8c6e47d39f83ae` |
| ldec.ko | `7663d3437220722858edfe024e75928648e40cd9345b0d6ee5ff3bf359c62f7e` |
| AP102 v3 serial.log | `743596129668f9abc19a1fa4eda1598d98453aa4c9189b0ccfa7370c2d793f84` |
| AP102 v3 cpio-audit.json | `b7a93032e7d984c02ef6956b35a11f58b22edbc78fae75ddea470415e6291962` |

其他输入大小、完整SHA及原始指令字节在 proof，脚本每次重新核验。

收尾连续两次退出0重建，proof 字节一致，SHA256 为 `b476dc7501110ce3792c373a63ddb1cb2795d0c3f151ab2c78469e98f091fb0e`；脚本语法、源守卫、全部资源区间、原失败分支与本目录仅三文件的边界检查均通过。

## 文件确实进入了 guest；索引能指向非零压缩数据

下面每项均在 `RUN/cpio-audit.json.members` 中存在，大小与 SHA 和 AP 原件完全匹配；这里没有将“主机存在”替代“CPIO 存在”。图像 `.uxc` 的实际 magic 均为 **`uxd\x07`**，不是普通 `uxc\x07` 字符串容器。（A1/A2：proof `resources.files[].cpio_member`。）

| guest `/usr/share/app/` 文件 | 字节 | 有效图像记录 |
|---|---:|---:|
| image_00_169.uxc | 27,969,292 | 7,735 |
| image_00_32.uxc | 26,839,932 | 7,735 |
| image_00_43.uxc | 27,607,512 | 7,735 |
| image_01_169.uxc | 25,397,076 | 7,569 |
| image_01_32.uxc | 25,508,264 | 7,569 |
| image_01_43.uxc | 25,349,968 | 7,569 |
| image_02_169.uxc | 5,576,672 | 1,910 |
| image_02_32.uxc | 5,532,880 | 1,910 |
| image_02_43.uxc | 5,732,624 | 1,910 |
| image.uxb | 2,281,172 | 831 内嵌 PNG |
| style.uxb | 540 | 本审计不解其样式字段 |
| color.uxb | 52 | 本审计不解其颜色字段 |
| global.xdb | 11,664 | `uxa\x07` 总索引 |

`global.xdb` 文件偏移 **3e1/409/435、471/499/4c5、501/529/555** 保存九份 `../../../usr/share/app/image_*.uxc` 相对路径；`1465/1471` 是 color/style 文件名。原路径拼接器 `1218a8–121918` 将资源库目录、`/` 与外部条目的文件名拼接，随后调 `117210→117168→117068`；后者 `117094` 调原 `open(path,0)`、检查文件长度，`1170f4→12e164` 建立映射。`MMapImpl` 的取数据槽为 `116d24: ldr x0,[x0,#0x40]; ret`。（A1：上述代码及 proof.resources.global_xdb_references。）

**运行正证据**：RUN serial LF **39902、39906、39907** 分别有 image_01_43、image_02_43、image_00_43 的原 proc maps；LF **41339、41341、41351** 有对应开放 FD。这证明至少这三份数据文件打开并映射成功，不能由缺少文件解释它们的全零目标；它仍不证明每条图片的读取/解码已经成功。其余六份仅有 CPIO 存在证据，不冒称本轮使用。（A2：proof.runtime.serial_snippets。）

## 原厂加载、索引、解码与写入链

| 环节 | 原行为 | VA / 文件证据 |
|---|---|---|
| 资源入口 | ux ResourceManager 的 setDatabase 转发至 libra；原 XDB 总表建立映射，再按 context/bank 取二级表 | `16ec6c→1188fc→11e2ac→1216a8`；总表 magic `uxa07` 在 `121590–12169c` 检查 |
| 查表 | context/bank override 的缓存匹配；外部 uxb/uxc/uxd 识别后，按 ID 查表得到记录 | `11e520–11e580、121954–121b80、121d08–121d7c、121e84–121fbc` |
| 实际整数索引 | 表布局低2bit决定 u16/u32/混合索引；u16索引乘4；FFFF 为缺项；混合表带长偏移。记录基址另加 header/table 长度 | `1213fc–121500`；脚本按原公式解析全部9文件，非 magic 扫描猜记录 |
| 图像属性 | 从图像记录提取 encoding、像素格式、宽高和可选 metadata；构造原输入流 | `113470–113744、114170–11437c` |
| 映射输入流 | type6 记录提供压缩长度和相对偏移；从对应文件映射创建有界流。无再经 CP 搬运的这条分支 | `114294–114324`：长度/偏移→映射引用→`128390` 或内存流 `12e508` |
| 解码命令 | DecodeImageCommand 执行，取源/目标对象并选工厂，返回解码 bool | RTTI vptr `257478`，execute 槽+20=`113fa0`；`113c80–113f10` 选 decoder，`11413c→134600→虚槽10` |
| 主批量分派 | encoding4/6 创建 Lz77Decoder；没有落入 libpng/zlib 软件解压 | DevDecoderFactory vptr `25d508`，槽+30=`15c6a0`；`15c6d8–15c6fc→154f18` |
| 硬件解压 | Lz77Decoder decodeImpl 打开 `/dev/ldec`，锁住目标位图，取得原目的 p32，提交同步 ioctl1 | RTTI=`25cc80`，vptr=`25cca8`，槽+18=`154c40`；`154c80、154cd8、154cf0、154e84` |
| 输出位置 | 输出是当前 ImageBufferAdapter/GraphicsImage 的位图子块；目的 p32 来自该对象虚槽，不是固定 Heap 地址 | `116870` 转发底层对象；`eecf8` 调位图虚槽+60取物理地址；`12b414→1167c8→15c1bc→153d08` 走 `BMP_WriteLockBits` |
| 回收/完成 | ioctl 返回后，原代码释放目标锁、关闭 fd，再返回 bool；命令销毁 decoder | `154ebc–154ec4、154d48–154d8c、114140–114158` |
| PNG 例外 | encoding1 选择0x80 PNG decoder；通过 libpng 读头/行/图像，再写 bitmap | `113e4c–113e64、15c64c–15c694、15f458`；不是 LDEC 路径 |

Lz77/Raw/Png 的 RTTI 与虚槽、ResourceManager/ImageData 公开符号、相关日志字符串全部收录在 proof.original_libObj。RawDecoder 虚槽实现为 `155198`，包含 CPU 原流读/格式转换；它是**另一个分派**，不能拿它的存在证明 encoding4 的硬件失败会自动回退。（A1：`15c6a0–15c7c4` 与两个 decoder 的独立虚表。）

### uxd 记录的已恢复子格式

限定本次 type6 记录，设记录起点 `r`、`q=r+4`：`u32[q]` 的 bit28..30 是 encoding，bit16..21 是资源像素格式；宽/高为 `u16[q+4/q+6]`。没有 bit27 可选属性时，长度/相对偏移在 `q+8/q+12`；有 bit27 时令 `n=u8[q+8]`，长度/偏移对改在 `q+12+8*n`。压缩源起点为 **`q+relative`**。bit31原样保留，**不将其单独解释成外部文件标志**。（A1：`1134d4–113578、113610–1136c4、113724/113740、114294–114320`。）

脚本核对所有有效记录的源区间、非零源内容、宽高及格式；全部源区间都在文件内。00组有4个FFFF缺项、01组有1个、02组有2个，这是表中的缺项，而非文件短缺。可选 metadata 确实存在，不能把所有记录都按固定20B解。（A1：proof.resources.files[].table/missing、metadata_ledger_sha256、all_payload_spans_valid。）

例如 `_43` 文件中可复核以下候选：

| 文件 / 表索引 | 记录偏移 / 压缩源偏移 | 宽×高 / 压缩长度 | LDEC 目标长度 / records |
|---|---|---|---|
| image_00_43 / 215 | `4e30 / a6a10` | 70×60 / 700B | 9,600B / 3 |
| image_01_43 / 1355 | `a740 / 26c030` | 320×52 / 1,369B | 33,280B / 9 |
| image_02_43 / 1228 | `6f04 / 3e0fc0` | 640×384 / 20,496B | 491,520B / 120 |

这些几何与图标/九宫格/面板吻合，**不是运行 resource ID 的身份绑定**。同尺寸记录有多个，不能只据尺寸选一个资源注入；精确记录偏移、完整描述符、压缩头/hash 在 proof.resources.files[].samples。（A1文件事实；角色对应B/U。）

## LDEC 原语义与当前最可能失败点

原 FX3 `ldec.ko` 是硬件驱动。初始化 `.text+5d8–65c` 注册字符设备/proc；`.text+720–774` 取得硬件基址并请求 IRQ。ioctl处理入口 `.text+870` 接受 **command1，复制32B请求**，pin住输入用户页，调用 DMA330 供数，再等待 LDEC 完成；它没有在CPU执行软件 LZ token 解码。主要依赖包括 `udif_cdev_register、udif_devices、dma330_mem_transfer_async、arch_p32_to_p64、get_user_pages` 和原IRQ机制。（A1：proof.original_ldec 完整 `.text/.init.text`、重定位和导入。）

| 请求偏移 | FX3 原类型 / 意义 | 原消费与构造 |
|---|---|---|
| +00 | u64 压缩源用户虚拟地址 | libObj `154db0`；驱动 `.text+980/984` |
| +08 | u32 压缩长度 | `154db8`；驱动 `.text+980` |
| +0c | u32 原生 p32 目的地址 | `154dc8`；驱动 `.text+938→arch_p32_to_p64` |
| +10 | u32 解压长度 | `154dd8`；驱动 `.text+964` |
| +14 | u32 records=`ceil(dstlen/4096)` | `154ddc–154de8`；驱动 `.text+a44` |
| +18 | u32 DMA channel，本调用写8 | `154de0`；驱动 `.text+92c` 检查≤15 |
| +1c / +1d | u8 source/destination cache bypass，本调用0/1 | `154dcc/154dc0`；驱动 `.text+954–978、bec–c14` 与供数函数 `.text+88–1c0` |
| +1e..1f | 保留，写0 | `154dd0/154dd4` |

libObj 输出长度是 **`align_up(width,16) * height * bitsPerPixel/8`**。资源格式0经 `111030` 的原表映射到系统格式7；系统格式7原描述是16bit，`1550f8–155158` 又明确按 LE16 的 R12/G8/B4/A0 四个nibble取通道。结合既有 GPE 映射，它是该批图像的 RGBA4444/fmt0工作域；不应把该压缩流交给 libpng，也不应把它冒认成标准zlib/LZ4。（A1：`1e3b48、264998、12fa94、154d90–154de8、101c74–101ca8`；具体压缩 token 语法U。）

完成语义是**同步 ioctl 返回**。驱动 `.text+88` 向 DMA330 提交并等供数回调，`.text+be0→hw_ldec_wait(.text+1098)` 等硬件IRQ；`hw_ldec_process .text+da8` 读取 `base+34` 并清 `base+30`：状态1→0成功、4→-5、其他→-13，然后唤醒等待者。超时分支返回-5；用户态检查负返回，成功后才正常解锁/关闭。该链没有 CP/UIPC/ICDT 完成包，不应补造这类通知。（A1：`.text+dc4–e60、1098–11a4、be0–c18`；libObj `154e84–154f14`。）

**当前 VM 证据（B强推断）**：

- `ldec.ko` 的23464B原模块存在于 CPIO，**没有** `/dev/ldec` 静态成员。init 会挂 devtmpfs，因此“CPIO 无节点”单独不足以证明运行缺节点。（A2：proof.runtime.ldec_cpio_members、init_devtmpfs_lines。）
- 保存的 init 模块列表只明确加载 OSAL/Backup/utimer/stream/DMM/GRM/upm/udate/kikilog 等，**没有加载 ldec 的命令**；serial 全文也没有任何 `ldec` 字样。原模块有真正 MMIO/DMA/IRQ 依赖，仅补 insmod 或空设备节点不会诚实地产生像素。（A1驱动与A2 init；proof.runtime.init_insmod_lines/serial_ldec_literal_count。）
- AP102 v3 共有 Heap **32** 次、Heap2 **699** 次纹理观察，全部四通道直方图仅bin0；TextHeap **63** 次完整观察有非零内容。池范围与本轮原日志 LF **8760、8783、8805** 对应：Heap `[410524000,410924000)`、Heap2 `[410924000,410c64000)`、TextHeap `[410c64000,410e64000)`。（A2：proof.runtime，统计是观察次数，不是唯一资源数。）
- 问题源正例：面板 `41059c400` seq678/LF153840；高亮 `410977d00` seq767/LF155672；图标 `41096aa40` seq701/LF154260、`41096bb00` seq720/LF154644、`41092c540` seq22/LF30677。均不是只看alpha，而是四通道全0。（A2：proof.runtime.selected_texture_observations。）

### 错误如何表现；没有把“无日志”当作成功

原 `154c80` 的 `open("/dev/ldec",2)` 若失败，`154c84` 按返回符号直接转向日志和 **`154c98: mov w0,#0`**；**不锁目标、不提交ioctl、不进入任何软件fallback**。若目的缓冲正是已观测的零内容，该路径会保持它为零。这是“纹理有对象/几何而内容空”的可行解释，不证明每个运行对象都走到了这里。（A1：`154c40–154cd8`。）

脚本在隔离 Unicorn 中执行上述原字节，只截获 open 与日志，open明确返回-1；结果原函数返回false、未触达ioctl、哨兵缓冲未变。该结果证明失败分支，不证明 AP102 的真实调用或 errno。（proof.open_failure_original_replay。）

原库**没有在此把失败改成true**：`11413c` 调decoder，`114140` 保存bool，`1140c4` 返回它。打开失败日志是 NOTIFY（80000000），经 `15ea44` 的全局 mask `264c08` 和 stella日志层输出；原镜像 mask 初值是FFFFFFFF，不能无证据断言本轮就是该mask把日志屏蔽了。ioctl失败另有错误/errno日志及诊断路径 `154ec8–154f14`。本轮未恢复bool在所有 worker/cache/UI 层的传播，**“错误被吞掉”仍U**；下一轮应同时抓返回值和队列消费，不能凭没有日志选定某个吞错点。（A1：上述地址；A2本轮无ldec日志。）

## 最小诚实软件实现规格（M；接口已恢复，位流解码仍有缺口）

实现目标应是该原 LDEC 原语的字节结果和完成合同。以下足以约束适配器，**不足以凭空实现 bit-exact LZ77 算法**；本目录没有提交软件解码器。（A1来源：上文32B ABI、工厂与驱动；U：proof.unproven。）

1. **输入绑定**：由真实 encoding4 资源记录/原流取得压缩指针和长度，保留 context/bank/resource ID、文件/hash/偏移、metadata 与源租约；按原目的bitmap锁取得输出格式、stride、子块身份。限定本批资源格式0→系统7，校验输出字节数与 `align16(width)*height*2`、records相符，不根据图标尺寸猜身份。（`114294–114324、154f18–154fe4、154d90–154de8`。）
2. **解压算法准入**：必须恢复并验证此 LDEC 位流的 literal/back-reference token、距离/长度、历史窗口、records边界、字典重置、尾部/错误规则。现在仅证明“硬件LZ77”，**尚无可用 token 语法或原像素oracle**；不能改用zlib/LZ4、简单RLE或把压缩字节memcpy进纹理。未知或不合法输入应拒绝并记录失败，禁止清零后回成功。（`ldec.ko .text+88、870–be8` 显示DMA/硬件消费；没有CPU token循环。）
3. **真实输出**：解码完整目标字节，包括原行padding，保持 LE RGBA4444。若在 ioctl 层适配，+0c的p32必须通过**原对象当前活跃映射/真实DMM转换**关联完整64位目的地址，不能统一 OR `0x400000000`；若在decodeImpl层适配，可复用原已持有的写锁逻辑指针，但不得重入该bitmap写锁。完整校验/解压到临时区后再提交，失败不覆盖目标；free/compaction与提交串行。（`154cd8、154cf0、154dc8`；驱动 `.text+938`；原位图锁入口 `153d08`，资源生命周期参见[extent审计](../gpe-fmt2-resource-extents/README.md)。）
4. **完成**：目标写入可见之后，准确返回 ioctl0/decoder true，让原代码解锁、关闭并推进命令；错误按真实失败返回。同步接口不另发UIPC/ICDT/GPE完成，也不提前ACK。保留 `software_LDEC=1 original_LDEC_hardware=0 bitstream_verified=<证据状态>`，不能让flags声称未完成的位流验证。（`154e84–154ec4、154d48–154d8c`；驱动 `.text+be0、da8–e60`。）
5. **验收**：先以已固定记录，例如70×60、320×52、640×384，取得独立可信解码/原像素对照，验证输出长度、padding、通道与透明边缘；再捕获同resource ID当前epoch写入→GPE源hash→当前bank提交。最后由运行链做原协议上下键与截图目视，确认高亮随焦点、图标内容和面板遮盖恢复，文字不回归。仅“输出非零”或同步返回0不构成正确解码。（原记录候选在本页及proof.resources；真实源结果在proof.runtime；独立oracle与新运行仍U。）

目前可以实施的是**被动采样和受约束适配外壳**，完整软件解码仍受第2项位流缺口阻止。不能将本文接口规格标成“解码器已经实现”。

## 下一轮运行验证点（本 worker 未执行）

优先一次被动采样即可区别文件/分派/设备/解码后的各分支。所有地址加本次libObj基址，hook须原字节/SHA守卫；记录完整线程、对象和同epoch身份，避免在持bitmap锁中做重入操作。（M；各VA均在proof.original_libObj.blocks。）

| 点 | 需要采样的变量/返回值 | 能关闭的缺口 |
|---|---|---|
| `121918 / 1219bc` | 文件路径、映射引用返回值；关联context/bank | 实际文件选择/打开失败 |
| `114294–114324` | type6记录、长度w24、相对偏移w25、q、真实源pointer/span/hash | 记录偏移/短读/空输入 |
| `15c6a0 / 15c700` | x1像素格式、w2编码、w3/w4宽高、x6/x7源/目标、返回decoder/vptr | 实际是否走Lz77与具体资源身份 |
| `154c40` | decoder+08源流、+10目标、+18格式、+1c/+1e宽高、+20源长 | 主链实际命中 |
| **`154c84`** | **open返回w0，立即保存errno；另只读检查 `/dev/ldec` 类型/major/minor及 `/proc/modules`** | **最优先：LDEC provider缺失是否真实发生** |
| `154cdc / 154cf4` | 写锁返回指针/stride槽；原目的p32与查询结果，关联父/子epoch及完整64位映射 | 目标映射/锁失败 |
| **`154e78–154e88`** | **x2所指32B ioctl结构（即当时x29+60），fd/request、源hash、ioctl返回/errno、目的前后hash与通道统计** | **设备存在但未解码/目的地址错误/假成功** |
| `154ec4 / 154d74` | 原decoder bool、解锁/关闭结果 | 解码失败与后续处理 |
| `114140 / 1140c4` | execute bool与对应command/request；继续跟worker消费/caching状态 | 全局吞错/失败缓存是否存在 |

如果 open失败成立，再研究/实现软件LDEC；如果open成功而ioctl未发生，转查源直指针/目标物理查询；如果ioctl报成功但目标不变，查provider是否空实现、p32映射和完成时序；如果目标已正确后又归零，沿free/compaction/后续writer追踪。每条分支分别需要实际采样结果，不在本轮预定结论。（M，原分支地址 `154c84–154ec4`。）

## 明确未证实项

- AP102 真实Lz77Decoder栈、open/errno、ioctl结果、运行log mask及所有有效preload对此链的影响。
- 高亮/面板/图标地址与具体resource ID、压缩记录、decoder实例的一对一绑定。
- LDEC压缩位流完整算法、独立正确像素及硬件逐位等价；不得以“同为LZ77”借邻机编码规则。
- `image.uxb` 本轮实际加载者及831个PNG的运行使用；global.xdb仅证明九份uxd与style/color引用。
- 失败bool是否在worker/cache/UI更上层被忽略，以及目标最初为何保持零的完整生命周期。
- 软件解码实现、guest新运行、高亮/面板修复与实机验收；本任务仅完成审计交付。

这些限制与 proof.unproven 同时保留；既有菜单可导航、命令result0和本次分支重放都不能代替图像解码/视觉修复回执。
