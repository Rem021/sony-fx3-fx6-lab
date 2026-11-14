#!/bin/zsh
set -eu
task_dir="${0:A:h}"
for cand_py in \
  "${FX3_PYTHON:-}" \
  "/Library/Frameworks/Python.framework/Versions/3.14/bin/python3" \
  "$HOME/.local/bin/python3" \
  "/opt/homebrew/bin/python3" \
  "/usr/local/bin/python3" \
  "$(command -v python3 2>/dev/null || true)" \
  "/usr/bin/python3"; do
  if [ -n "$cand_py" ] && [ -x "$cand_py" ]; then
    exec "$cand_py" "$task_dir/run_probe.py" --profile minimal-linux --seconds 12
  fi
done
echo 'Python 3 not found' >&2
exit 2
