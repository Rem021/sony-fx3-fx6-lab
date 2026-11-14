#!/bin/zsh
# FX3 TRY2 local trial (supports internal SSD & legacy KAFU2T).
export PATH="$HOME/.local/bin:/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
script_dir="${0:A:h}"
rel_runner='work/fx3-vm-20261101/lead-codex/vm-optimization-20261103/runtime/try2-delivery/run_trial_v4_try2.py'
runner="/Volumes/KAFU2T/AI/Projects/Mac/$rel_runner"
for base_mac in "${script_dir:h:h:h:h}" "$HOME/AI-Workspace/AI/Projects/Mac"; do
  if [[ -f "$base_mac/$rel_runner" ]]; then
    runner="$base_mac/$rel_runner"
    break
  fi
done
python_bin=""
for cand_py in "$HOME/.local/bin/python3" "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" "/opt/homebrew/bin/python3" "$(command -v python3 2>/dev/null || true)"; do
  if [[ -n "$cand_py" && -x "$cand_py" ]]; then
    python_bin="$cand_py"
    break
  fi
done
if [[ ! -f "$runner" || ! -x "$python_bin" ]]; then
  print -u2 'TRY2 入口文件或 Python 3 缺失，请查看同目录的 TRY2-使用说明.md。'
  exit 2
fi
print '正在启动 FX3 TRY2，本机网址：http://127.0.0.1:8765'
print '保持本终端开启；网页点击「结束试用」或在此按 Ctrl-C 后，等待退出回执。'
print '如提示已有 FX3 运行，请等待占用者结束，不要删除锁文件。'
exec "$python_bin" -B "$runner" --port 8765 --max-minutes 15
