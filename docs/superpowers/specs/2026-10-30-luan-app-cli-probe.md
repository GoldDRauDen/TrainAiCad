# Luan App — `claude -p` probe (Claude Code 2.1.301, 2026-10-30)

Command (throwaway worktree of `origin/main`, model haiku, cost $0.013, 6 turns, 21 s):
`claude -p "<edit rules/BEND.md; git status; write out.txt; python tools/job.py --help>" --output-format stream-json --verbose --permission-mode dontAsk --model haiku --allowedTools Read Glob Grep Write Edit "Bash(python:*)" --disallowedTools "Bash(git:*)" "Edit(rules/**)" "Write(rules/**)" --add-dir %TEMP%\luan_probe`

| Check | Result |
|---|---|
| Edit `rules/BEND.md` | denied: tool_result `is_error: true`, `File is in a directory that is denied by your permission settings.`; file unchanged |
| `git status` | denied without hanging: `system/permission_denied` event + tool_result `Permission to use Bash with command git status has been denied.` |
| Write into `--add-dir` | allowed |
| `python tools/job.py --help \| head -3` | allowed (`Bash(python:*)` covers a pipe to `head`) |
| worktree `git status --porcelain` after | empty |

Event shapes used by the runner:
- `{"type":"system","subtype":"init","cwd","session_id","tools","model","permissionMode",...}`
- `{"type":"assistant","message":{"content":[{"type":"tool_use","name","input"}|{"type":"text","text"}]}}`
- `{"type":"user","message":{"content":[{"type":"tool_result","is_error","content"}]}}`
- `{"type":"rate_limit_event","rate_limit_info":{"status":"allowed_warning","resetsAt":<epoch>,"rateLimitType":"seven_day","utilization":0.27,"unifiedWindows":{"five_hour":{"utilization","resetsAt"},"seven_day":{...}}}}` → usage limit = `status` not starting with `allowed`; pause until `resetsAt`; utilization shown to Admin.
- `{"type":"result","subtype":"success","is_error":false,"result","num_turns","duration_ms","total_cost_usd","usage":{"input_tokens","output_tokens","cache_read_input_tokens","cache_creation_input_tokens",...},"permission_denials",...}`
- Other `system` subtypes (`thinking_tokens`, `task_summary`, `post_turn_summary`, `commands_changed`) are ignored.

Decision: keep path denylist (works) + worktree isolation + post-run `git status` check.
