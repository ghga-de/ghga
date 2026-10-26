#!/usr/bin/env bash
# `just testbed-trace [file]`: open a Playwright trace from a traced test-bed run
# (`TB_TRACE=1 just testbed -m frontend`). With no argument, lists what the last traced run
# left behind. `show-trace` would otherwise try to launch a GUI chromium, which there is no
# display for in the devcontainer, so serve the viewer instead and let the editor forward
# the port.
set -euo pipefail

file=${1:-}
dir="${TB_TRACE_DIR:-$PWD/testbed/.traces}"
if [ -z "$file" ]; then
    ls -1 "$dir"/*.zip 2> /dev/null \
      || { echo "no traces in $dir — record some with \`TB_TRACE=1 just testbed -m frontend\`"; exit 1; }
    echo
    echo "open one with: just testbed-trace <name>"
    exit 0
fi
# accept a bare test name, a file name or a path
trace="$file"
[ -f "$trace" ] || trace="$dir/$file"
[ -f "$trace" ] || trace="$dir/$file.zip"
[ -f "$trace" ] || { echo "error: no such trace: $file (\`just testbed-trace\` lists them)" >&2; exit 1; }
echo "serving $trace on http://localhost:9323 (ctrl-c to stop)"
.venv-testbed/bin/playwright show-trace --host 0.0.0.0 --port 9323 "$trace"
