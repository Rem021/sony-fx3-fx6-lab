# 收紧前的成功构建与测试

此处保留收紧前的源文件、构建回执、日志、主机传输/测试源码和模拟库。回执原有路径未改写：原来的 `artifacts/private-libusb` 对应本目录 `private-libusb`；原生构建树位于 `../work/native-build-before-budget`；原测试位于 `../run-transport-tests-before-budget`。这些只是历史字节，不是当前候选的运行放行。

当前构建另外收紧为普通 MSC PID 0DA1、单次显式设备描述符请求、多配置拒绝，并补齐两个拒绝分支的 IOObject 释放。
