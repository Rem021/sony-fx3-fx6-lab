#!/bin/zsh
# FX3 TRY2 local trial. Keep this Terminal window open while using the web page.
runner='/Volumes/KAFU2T/AI/Projects/Mac/work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/run_trial_v4_try2.py'
python_bin='/Library/Frameworks/Python.framework/Versions/3.14/bin/python3'
if [[ ! -f "$runner" || ! -x "$python_bin" ]]; then
  print -u2 'TRY2 入口文件或 Python 3.14 缺失，请查看同目录的 TRY2-使用说明.md。'
  exit 2
fi
print '正在启动 FX3 TRY2，本机网址：http://127.0.0.1:8765'
print '保持本终端开启；网页点击「结束试用」或在此按 Ctrl-C 后，等待退出回执。'
print '如提示已有 FX3 运行，请等待占用者结束，不要删除锁文件。'
exec "$python_bin" -B "$runner" --port 8765 --max-minutes 15
