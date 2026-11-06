# VDF 0x147 与 OSD 扫描输出审计

2026-11-01。结论：**0x147 是 YUV 布局选项表，不是 24 个像素平面描述符**。AP 构造函数 `appFw 0x2deb060` 写命令 0x147、长度 0x308；CP RTTI `N3VDF29VdfInputCmdSetYuvLayoutOptionE @0xb3d6b0`、vtable `0xb7e5d4` 将执行绑定到 `0x1dc170`，旧协议 ID 为 2001/030b（`0x5f60c4`）。所以这份表不能直接提供菜单 PNG 所需地址、stride、格式、alpha、层序或当前像素 bank。

仅静态读取原件与已有日志，输出仅本目录；未启动 QEMU、未连接 QMP、未改 runtime 或固件。`vdf0147-proof.json` 保存原件 SHA256、原始指令字节/VA、完整请求、24 行解码、日志行号和未证实项。未取得新 guest 帧或实机回执。

## 复现

项目根执行：

```sh
work/sony-firmware-20261024/stage4-windows-collab/mac-verification/.venv/bin/python work/fx3-vm-20261101/lead-claude/audits/vdf0147-plane-scanout/audit_vdf0147.py
python3 work/fx3-vm-20261101/lead-claude/audits/vdf0147-plane-scanout/dump_osd_frame.py --self-test
```

两者退出 0；前者重建 proof，后者重建 `synthetic.raw`、`synthetic-planes.json`、`synthetic.png`、`self-test.json`。后者仅用 Python 标准库，测试覆盖 4444 分量、LE16/LE32、>4GiB 地址、行 padding、不同层序/半透明 source-over、裁剪、ARGB 映射、透明/强制不透明、PNG 解压和五类错误输入；**合成测试不能证明原厂 alpha 规则或当前菜单可见**。`inspect_static.py` 为辅助只读反汇编器，正式审计脚本不依赖它。

## 完整请求与字段

AP66 `runs/ap66lut-ed5764ad/serial.log:20140` 与 AP70 `runs/ap70lcd-f61554d9/serial.log:20315` 均有完整 1552 个 hex 字符。两者与 AP52 `ap52-plane-observe/0147-native-request.bin` 全部相同，SHA256 `981f6f27a9cde5f695b181570c0d187596853216428baca898a395f692aedd5d`。脚本检查 776B 长度及逐字节相等，不从截断日志补零。

8B 头部是 LE16 `{0x200d,0x0147,0x0308,0x8001}`；记录 `q = request+8+32*i`。AP `0x2deb0a4–0x2deb0bc` 写头，`0x2deb2e4–0x2deb3c0` 构造24行，`0x2deb3c4–0x2deb3e4` 发往 `0x92840747` 并等待12B回复。调用链为 `0x2bb9554 → 0x2dcffd4 → 0x2deb060 → 0x2de70a8`；AP70 原生栈返回地址 `0x2deb3e8/0x2dd0000/0x2bb9558` 相符。AP 字符串 `vdf_set_yuv_layout_option @0x39691c8` 在 `0x2deb170` 使用。

| q 偏移 | 编码 | 能确认的用途 / 原代码 |
|---|---|---|
| 0 | u8 | 输出选择 bitmask；捕获分组1、2、4。CP `0x1b5e6e–0x1b5eae` 重建各位；不只是软件模型限定的低3位 |
| 1 | u8 | 二值模式；CP `0x1b5de8–0x1b5e00` 检查<2；`0x1dc376–0x1dc37a` 非零时跳过矩形边界校验。**不能据此命名 active/enabled** |
| 2 | u8 | AP清零，未见消费；`0x2deb32c` |
| 3 | u8 | 布局 ID；捕获0..7，CP桥 `0x1b5e02–0x1b5e1a` 检查<8；不是已证实的物理平面ID/层序 |
| 4,6,8,10 | u16×4 | 矩形A `(x,y,w,h)`；AP `0x2deb32c–0x2deb338`；CP `0x1dc39a–0x1dc3c2` 校验 x+w/y+h |
| 12,14,16,18 | u16×4 | 矩形B `(x,y,w,h)`；AP `0x2deb340–0x2deb368`；CP `0x1dc3c4–0x1dc3ee` 校验。A/B准确 source/destination 域未闭合 |
| 20 | u8 | 第二布局选择项，样本等于 q3；CP `0x1b5e1c–0x1b5e34` 检查<8，不能命名 alpha |
| 21 | u8 | 二值选项；CP `0x1b5e36–0x1b5e4e`；捕获全0 |
| 22,23 | u8×2 | AP初始清零，桥未复制；CP `0x1dc38a–0x1dc396` 依子系统类型保留或清零；作为几何域选择传 `0x60e8f4/0x60e90c`，不是stride |
| 24 | u8 | 0..3选项；CP桥 `0x1b5e50–0x1b5e6a`，处理 `0x1dc3fa–0x1dc3fe`；捕获0 |
| 25..27 | bytes | AP零填充，桥不拷贝，准确保留语义未证实 |
| 28 | u32 | 通用选项字，CP `0x1b5ee6–0x1b5eea` 拷贝；捕获全0，未证明其非零语义；不得解释为DMM句柄 |

下表逐条给出全部变化字段；A 均 `(0,0,640,480)`，q2、q21..q31 均0，q20等于ID。共同零字段也逐字段保存在 proof。**输出1=LCD、2=EVF、4=HDMI 是待核对的常见映射候选，本审计没有足够枚举证据确认名称，工具不会依此自动选择屏幕。** CP校验和AP构造只证实选择掩码/布局关系。640×428 是矩形B，不能当作菜单像素buffer的高。

| 记录i | 输出mask | q1模式 | 布局ID=q20 | 矩形B x,y,w,h |
|---:|---:|---:|---:|---|
| 0 | 1 | 0 | 2 | 0,0,640,428 |
| 1 | 1 | 1 | 1 | 0,60,640,360 |
| 2 | 1 | 0 | 0 | 36,0,568,428 |
| 3 | 1 | 0 | 4 | 106,0,428,428 |
| 4 | 1 | 1 | 5 | 0,48,640,384 |
| 5 | 1 | 1 | 6 | 0,71,640,338 |
| 6 | 1 | 1 | 7 | 0,71,640,338 |
| 7 | 1 | 1 | 3 | 0,0,0,0 |
| 8 | 2 | 1 | 2 | 0,26,640,428 |
| 9 | 2 | 1 | 1 | 0,60,640,360 |
| 10 | 2 | 0 | 0 | 35,26,570,428 |
| 11 | 2 | 0 | 4 | 106,26,428,428 |
| 12 | 2 | 1 | 5 | 0,48,640,384 |
| 13 | 2 | 1 | 6 | 0,71,640,338 |
| 14 | 2 | 1 | 7 | 0,71,640,338 |
| 15 | 2 | 1 | 3 | 0,0,0,0 |
| 16 | 4 | 0 | 2 | 80,0,480,428 |
| 17 | 4 | 0 | 1 | 80,60,480,360 |
| 18 | 4 | 0 | 0 | 106,0,428,428 |
| 19 | 4 | 0 | 4 | 160,0,320,428 |
| 20 | 4 | 1 | 5 | 20,0,600,480 |
| 21 | 4 | 0 | 6 | 80,71,480,338 |
| 22 | 4 | 0 | 7 | 95,71,450,338 |
| 23 | 4 | 1 | 3 | 0,0,0,0 |

## 配置 bank 与像素 bank

CP桥 `0x1b5cf8` 为旧030b分配临时DMM unit0x409（`0x1b5d36`），把24条转换后的32B记录存进去，旧16B消息携带其DMM handle（`0x1b5f14–0x1b5f3e`）。**这个handle承载布局表，不承载菜单像素**。处理函数 `0x1dc230–0x1dc252` 先验证再调用配置缓存；`0x1dc26a` 释放临时DMM后于 `0x1dc282` 回复130b。桥 `0x5c9858` 形成12B 1147回复，故ACK不等于一帧显示完成。

CP `0x5f161a` 读对象+0x604选择位，`0x5f1624/0x5f162c` 选+0x304或+4这两个768B表，`0x5f162e` 翻转位，`0x5f164e` 拷贝表；`0x5f1666 → 0x5f1356` 发送内部 `2001/f024/12B`，+8是刚保存的表指针（`0x5f138c`）。f024在CP内部产生，不是菜单AP发出的flip命令。接收端最终如何应用该YUV布局尚未闭合。软件 `fx3-vdf-plane.c` 的 `next_bank/pending_f024` 仅模拟这段缓存行为；AP70日志明确 `pixels=0 active_output=0 original_CP=0`。

独立的像素缓冲指针交换位于 **libObj `0xf33d0`**：加锁，若对象+0x70为0，则 `0xf33ec–0xf33f0` 交换+0x60/+0x68两个指针；`0xf335c` 与 `0xf3368` 分别读两侧对象。上层 `0xf2fa0` 非零发布分支在 `0xf2ffc` 调交换，再从 `0xf300c–0xf3020` 取得buffer关联信息。**没有证据表明这个交换由0x147 bank或f024驱动；第二buffer物理地址与当前已扫描一侧未证实。**

## 绘制完成后的发布路径

这里能给出AP原码中的候选发布链，不能声称AP70已执行完成菜单发布：

1. libObj `0xf2fa0` 非零分支交换buffer，`0xf305c → 0xf2428` 把buffer关联字段封成40B本地消息；`0xf1fbc` 分配并设置u16 ID=1（`0xf2034`），`0xf233c–0xf235c` 用 `osal_snd_msg` 发往 **0x8288076c**。0xf2fa0零参数分支走另一条控制消息（`0xf3084 → 0xf2380`）。
2. 本地线程 `0xf2820` 在 `0xf28b4–0xf28e8` 分发0x8288076c到 `0xf27d8 → 0xf2638`。绘制帧路径先向0x8280074d发12B ID1002、+8=1003的控制（`0xf268c–0xf2698`、`0xf1d90`、`0xf25f4`），再分配36B、u16 ID **0x1003** 的消息（`0xf1e1c–0xf1e98`）。
3. `0xf26e0–0xf274c` 填入从40B本地消息提取的u32关联ID、模式、矩形和末尾word，`0xf2758–0xf2760` 用 `osal_snd_msg` 发向 **0x8280084d**。这是继续追踪OSD发布的准确入口，尚未闭合到VDF pin接收者/CP物理地址/显示完成。

这里关联ID只以u32字段报告；在映射接收者前不冒称其一定是DMM句柄。libObj `GRM_fbrmPrepareUpdateYUV @0xf3924`、`GRM_fbrmUpdateYUV @0xf3934` 实际都是 `mov w0,0; ret`，不能因为函数名把它们当作原厂发布实现。`GraphicsEngine::drawFramebuffer @0x16ea10` 经过若干间接绘图接口，尚未把菜单绘制、GPE完成、上述发布路径三者全链绑定。

其他命令也分开：0x159 OSD on/off 是门控；既有审计的原路径为内部f030，无回复，并非像素flip。另一个原类 `VdfInputSetOsdLayout` 的旧命令0306在CP `0x5f56b8`，执行 `0x5f56ee`，内部发送 **f031**（`0x5f5752–0x5f5768`），同样不能与0x147/f024互换。`VdfInputCmdUpdateYuv` vtable `0xb7e634`、Activate `0x1dc4b8` 是YUV更新类；没有原码证据允许用它冒充菜单OSD发布。

## 物理地址来源及离线导出规格

GPE FillRect目标是参数+0的 **完整u64物理地址**（libgpe `0xc61c`），stride是+0x18像素数（`0xc610/0xc664`）。BitBlit目标+0、目标stride+0x30、格式+0x34；快路径按 `0xb354–0xb3c8` 计算偏移。原DMM映射转换（libObj `0x102b98`）是经区间检查的 `physical_base + (logical-logical_base)`；GetDmmMemInfo `0x101d84` 最终输出physical/logical/size（`0x101e0c–0x101e20`）。libObj像素对象分配/映射的另一入口 `0xf16b0` 在 `0xf1778` 调 `0x102434`，`0xf17ac` 调 `0x1026b4`，不能拿布局表临时unit409代替该分配生命周期。

既有实测限于DMM extent type/handle545、base **0x43feb5000**、size0x140000，首payload **0x43feb5100**。AP70 `FX3_GPE_UNIFORM_DONE` 记录后者614400B/480行，对应640×480×2字节。该extent与已清屏目标的对应有日志依据（另见 `reports/2026-11-01-fx3-vm-resumed-repair/uniform-surface.md`），**没有当前scanout绑定证据**；+0x100只适用于这一次观察，不能推成所有DMM或第二buffer的固定公式。

对已经由运行链授权取得的pmemsave原始文件，输入JSON必须显式提供以下内容，不能由0x147补齐：

```json
{
  "dump_base": "0x43feb5000",
  "width": 640,
  "height": 480,
  "background": [0, 0, 0, 0],
  "planes": [{
    "address": "0x43feb5100",
    "width": 640,
    "height": 480,
    "stride_pixels": 640,
    "format": "format0-le16",
    "component_order": "RGBA",
    "alpha_mode": "straight",
    "global_alpha": 255,
    "x": 0,
    "y": 0,
    "z": 0
  }]
}
```

上述JSON是**基于已观察地址的解释示例**，RGBA和straight是调用方假设，不能当作已恢复的当前菜单参数。按需以`opaque`导出原分量以便比较；工具明确拒绝未验证的premultiplied模式、格式2/3/4。调用：

```sh
python3 dump_osd_frame.py captured.raw planes.json frame.png
```

地址计算精确为 `file_offset = address - dump_base + ((y*stride_pixels)+x)*bpp`。format0 bpp=2，读取LE16，按bit12/8/4/0取nibble乘17。format1 bpp=4，读取LE32，按bit24/16/8/0取byte。两者c0..c3再由显式`component_order`置换到RGBA。原厂格式0的证据**仅到位置与打包**（libgpe `0xc400–0xc428`：`c0>>4<<12 | c1>>4<<8 | c2>>4<<4 | c3>>4`）；格式1在 `0xc390–0xc39c` rev32。RGB/A名字、色域、transfer、是否预乘均未证实；黑色清屏没有通道辨识力。

多平面按**调用者指定、不得重复的z升序**从后向前做8bit straight source-over，alpha乘global_alpha/255，四舍五入。真实OSD/YUV/底图的排序和混合数学未闭合，此为离线工具的定义，不能假称CP算法；不支持缩放旋转、YUV或CLUT。平面在dump中的每行span必须完整，越界拒绝；画布以外只裁剪输出位置。可捕获extent全段，或仅捕获目标payload span `((height−1)*stride_pixels+width)*bpp`，并同步改变dump_base。

[QEMU官方pmemsave接口](https://www.qemu.org/docs/master/interop/qemu-qmp-ref.html#command-pmemsave) 定义输入为guest物理起点`val`、字节数`size`与输出`filename`；本次仅核对接口文档，不执行它。导出者还须冻结/标记同一时刻的活跃DMM、buffer选择、GPE完成和发布状态；单个pmemsave文件没有“当前菜单帧”身份元数据。后续运行链可先在GPE完成点取同一已知buffer做离线图像诊断，闭合0x8280084d接收者后才把它升级为scanout回执。

## 剩余证据门槛

输出mask与LCD/EVF/HDMI的精确枚举映射、布局ID具体名称、A/B域与额外选项语义、当前扫描侧/第二像素buffer地址、消息0x1003到CP/扫描DMA的消费链、真实菜单发布命中、RGBA名称和预乘/混合/多平面层序均未证实。原始VA证据可复跑，但当前结果不能声称菜单帧导出已完成，也不能把合成PNG当作guest菜单截图。
