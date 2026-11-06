# 来源与适配边界

本工具为当前Mac项目新编写的离线文件适配实现。没有导入、执行或分发社区的相机运行时、USB会话、root工作器或Sony固件。

参考：

- [YuuLuo固定构建器](https://github.com/YuuLuo/a7c2-camera-tools/blob/f124d87c26110a82db54775bfa64a0843ff21410/windows/runtime/core/build_p1_gate_200.py)：参考原件全指纹、固定长度压缩与原字节逆修改的设计。该文件SHA为`c065a0d96ced68ffb0cee11d82aeab2734614a49e38704438d1ec70d32a23169`；未导入其`mac_probe_fl23`或native模板。
- 同提交的`windows_p1_capture.py`、`p1_fixed_host_export_201.py`、`p1_block_window_protocol_201.py`与`volatile_p1_window_201.c`：参考定长块、窗口链和短读拒绝的设计，0.2重新编写本地主机读取实现，没有复制社区的设备wire、252:129节点绑定、Sony认证或加载器。社区构造函数先删除`/etc/ld.so.preload`再检查tmpfs／请求；“分区只读”不能扩展为整个采集过程无持久写入。逐文件SHA及所读固定提交见第186轮`source-review.json`。
- 本项目既有`work/fx3-color-port-20261027/input-20261028/read_squashfs4_gzip.py`：派生只读SquashFS解析器，原SHA`0f9eea50595f3a5e17d37f2f53bd8c40b582b4d22f4b8cec9da571ed2cb56ad2`。改为显式错误检查，并增加解压、元数据跳数与目录深度限制。
- Linux SquashFS4／gzip结构及Microsoft FAT格式；仅解析，不挂载、不创建源镜像中的设备或链接。

参考程序、镜像及机身原件不包含在源码发布包。官方2.04／2.05镜像的来源、哈希与原指令证据沿用项目已保存的Sony原件；运行工具时读取本地已有文件，不自动下载。

Python命令不包含实体相机访问、授权状态覆盖、密码／密钥收集或自动重试。未来实际设备后端仍需要实现、评审及具体授权；这些步骤尚未发生。

0.3补充：Python命令仍仅处理本地文件；新增`native/fx3_p1_reader.c`包含未来在Linux机身侧执行的固定分区只读候选，**尚未链接、部署或运行**，并非已接通的设备后端。它是重新编写的显式入口，不含社区构造函数或加载器。`BLKGETSIZE`沿用本项目对FX3原DeviceIo的既有指令证据，stat／statfs使用Linux4.9 asm-generic UAPI布局，当前Sony内核兼容性仍需独立验证。普通Mac测试构建只通过显式自建系统调用边界运行，不把Linux syscall号传入macOS。

0.4补充：C工作器源码保持0.3的固定SHA，新增自写`entry.S`与`elflink.py`，依据[Arm AArch64 ELF ABI](https://github.com/ARM-software/abi-aa/blob/main/aaelf64/aaelf64.rst#576static-aarch64-relocations)实现当前两个对象所需的5类重定位。它是限定构建器，不是完整通用链接器，也不复用或分发Sony模块。生成ELF只在自建ARM64模拟环境与假系统调用中验证，尚未在机身部署。既有Unicorn及Capstone仅供测试使用，不包含于源码包；工具主机命令不载入或执行目标ELF。

0.5补充：新增自写boot0／boot1候选C、显式汇编入口、独立wire及本地解码／组装；现有链接器只增加第二个固定函数名，不增加重定位类型或任意导入。使用第213／214轮公开7.02主系统原模块的文件SHA作为有限的过滤条件，原模块本身不分发、不加载或执行。当前机身已加载驱动、p1身份、实际数据视图和恢复均未证。参考[Linux v4.9 BLKGETSIZE定义](https://github.com/torvalds/linux/blob/v4.9/include/uapi/linux/fs.h)核对512字节扇区单位，不以通用文档替代Sony内核实测。C内SHA-256为本项目自写实现，使用hashlib及公开模块普通文件验证。所有设备调用在测试中均为显式夹具；源码包不含Sony固件、生成的机器码或相机启动器。
