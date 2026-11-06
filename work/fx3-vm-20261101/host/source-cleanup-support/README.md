# 本轮第三方源码清理说明

仅删除本轮 `host/sources/qemu-11.1.2`（含固定提交的内嵌 DTC）及 `host/downloads/qemu-11.1.2.tar.xz`。没有操作其他项目、旧材料、Sony 固件、原运行记录或正式交付包。

`qemu-original-to-fx3-complete.patch` 完整保存本轮唯一代码改动；对照源归档检查了 78,695 个普通文件成员。其余三项差异仅为一个未提取的绝对符号链接和两个尾斜杠规范化的相对链接。DTC 已跟踪文件无改动。来源 URL、版本、SHA 与 DTC commit 在上级回执和既有来源回执中。

保留 `host/build` 的编译产物及日志/元数据、`build-venv`、`deps`、`pkgconfig`、二进制 bottle 缓存。它们是本轮局部构建环境，不是正式运行包的依赖；`build` 中指向已清源码的符号链接会失效，恢复同版源码后才可重新构建。本轮未扩大清理到这些可复用缓存。

按固定 QEMU URL 重取并核 SHA 后，在原 `sources/qemu-11.1.2` 路径展开，应用本目录完整 patch；Meson 会按 `internal-dtc-receipt.json` 固定提交取 DTC。依赖来源以既有 `source-receipt.json` 和 `dtc-source-receipt.json` 为准。重建配置/命令与日志保留在 `configure-02-command.json`、`build-command.json`、`configure-02.log`、`build.log`；正式包重定位和重新签名过程另见封存的 `outputs/fx3-vm/metadata/`。清理后未执行重建，也未再次启动 VM。

`licenses/` 只新增许可证文本；`library-license-sources.json` 记录三份非系统动态库的许可与可重取来源。封存的 `outputs/fx3-vm` 及原 FX3 输入保持原 SHA。完整逐文件核对、Mach-O 相对路径闭包、无 LC_RPATH 与签名只读核验结果见上级清理回执。
