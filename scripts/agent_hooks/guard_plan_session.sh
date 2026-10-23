#!/bin/sh
# Fast path for guard_plan_session.py, which runs on every tool call in this repo:
# a call that is not an artifact call, in a session that holds no lock, needs no
# Python start-up. Without jq, every call goes to the Python guard.
input=$(cat)
if [ "${GHGA_PLAN_GUARD:-}" = off ]; then exit 0; fi
state="${GHGA_PLAN_GUARD_STATE:-$HOME/.claude/define-tasks-guard}"
if command -v jq >/dev/null 2>&1; then
  {
    IFS= read -r session
    IFS= read -r tool
  } <<EOF
$(printf '%s' "$input" | jq -r '.session_id // "", .tool_name // ""' 2>/dev/null)
EOF
  case "$tool" in
    Artifact | ArtifactData | ArtifactComments) ;;
    *) if [ -n "$session" ] && [ ! -e "$state/locks/$session.json" ]; then exit 0; fi ;;
  esac
fi
printf '%s' "$input" | exec python3 "$(dirname "$0")/guard_plan_session.py"
