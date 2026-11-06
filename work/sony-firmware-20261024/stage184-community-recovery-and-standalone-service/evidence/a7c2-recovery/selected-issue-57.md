https://github.com/QAQLeonard/a7c2-fl23-research/issues/57
[A7C II 2.01 / macOS / Tools 3.0.3] 只读 USB 稳定性检测第 1 轮即失败：读取 /usr/lib/appFw.so 返回 Jiritsu 狀態 0x10000004（机身曾由索尼官方更换主板）
## 环境

- 相机：Sony ILCE-7CM2（A7C II），固件 2.01；**此前由索尼官方更换过主板**。此前未使用本项目或任何非官方修改。
- 电脑：macOS（Apple Silicon）；A7C2Tools 3.0.3（macOS arm64 安装包）。
- 相机 USB 模式：海量存储（MSC）。

## 操作与结果

1. 「准备 USB 服务连接」**成功**：`054C:0E8A` 正常检测、驱动准备完成，日志出现「服务连接成功，驱动准备结束」，之后相机恢复到普通 USB。服务连接与驱动这一步本身没有问题。
2. 点「检测 USB 连接稳定性（只读）」**必失败，且每次都在第 1 轮就停**：

```text
USB 稳定性检测未通过（第 1 轮）：Jiritsu 狀態 0x10000004。
请换线或直连电脑 USB 接口后重测；本次没有固件或设置写入。
```

3. 完整 traceback（取自本机 `~/Library/Application Support/A7C2Tools/runs/`）：

```text
File "src/desktopapp/usbcheck.py", line 55, in run
    raw = camera.read(path)
File "src/looks/looktool/devicesession.py", line 102, in read
    try:return self.link.read('/tmp/jiritsu/../../'+path.lstrip('/'),missing)
File "src/camera_runtime/transport.py", line 416, in read
    def read(self,path,missing=False):self.select(path);return self.jiritsu(17,b'\0\xff\0',missing)
File "src/camera_runtime/transport.py", line 411, in jiritsu
    if status:raise RuntimeError(f'Jiritsu 狀態 {status:#x}')
RuntimeError: Jiritsu 狀態 0x10000004
```

4. 「一键安装」也停在同一步，没有进入写入阶段。
5. 每次失败后工具都会让相机退出服务模式；拔线后相机取景、拍照、回放均完全正常。

## 已排除的变量

本机 `runs` 目录下共有 **6 次 `usb_stability` 记录，6 次全部在第 1 轮以完全相同的 `0x10000004` 失败**。期间换过多根数据线、多个 USB 口和多台 Mac，结果一致。

也就是说这不是间歇性掉线或接触不良，而是**确定性的、可 100% 复现的读取失败**。README 里「换线 / 换口后重测」的排查路径对本案无效。

## 一个可能相关的线索

读取路径是 `/tmp/jiritsu/../../usr/lib/appFw.so`，即经由 `/tmp/jiritsu` 做路径穿越。而本项目 issue #23 记录过：A7C 一代上首次 Jiritsu 文件命令在

```c
mount("/dev/nflasha6", "/tmp/jiritsu", "vfat", ...)
```

处**返回 `0x10000004`**（`sys_mount` 只把 `EBUSY` 当作「已经挂载」）。

这台机身更换过主板，**NAND 分区布局有可能与作者验证时使用的机身不一致**，因此我怀疑失败点落在 `/tmp/jiritsu` 的挂载 / 访问上，而不是线材或 USB 传输稳定性。

这只是我的猜测，没有实测依据，仅作定位参考。

## 想请教

1. `0x10000004` 在 A7C II 上代表什么？仓库源码里只见到 `0x10000006`（文件缺失）被定义，`0x10000004` 没有找到任何定义或文档说明。
2. 更换过主板的机身是否可能落在工具的支持范围之外？
3. 在拿到诊断包之前，我是否应该完全停止重试？（目前我**没有**重复写入任何内容，每次都停在第 1 轮的只读检测。）

诊断包已可导出，需要的话请告知，我会贴到这里。在得到你的判断之前，我不会重试安装，也不会执行「恢复原厂功能」。

Related：#23（`0x10000004` 出现在 A7C 一代 `mount /tmp/jiritsu`）、#46（macOS 3.0.3 安装停在 appFw.so 相关步骤）、#28（`appFw.so 0x3528804` 补丁位置冲突）。
