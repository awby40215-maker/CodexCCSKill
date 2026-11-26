# Optional CodexCCSKill Guard

The guard loads the installed skill at the start or resumption of a local Codex conversation and initializes checks for each turn. On supported tool paths, it checks the working directory and patch targets. At the end of a turn, it can ask Codex to continue when a tracked edit has no passing final verification. A continuation may run again when it records a new edit. Without further verifiable changes, the guard surfaces the pending acceptance instead of looping.

## Install on macOS

Install the [standalone skill](../codexccskill/README.md) in the user skills directory first. The guard uses the Python 3.9+ standard library and requires a local Codex client with lifecycle hooks. From the repository root:

```sh
mkdir -p "$HOME/.codex/hooks/codexccskill-guard"
cp guard/guard.py "$HOME/.codex/hooks/codexccskill-guard/"
```

Merge the following entries into the user `hooks.json` at `~/.codex/hooks.json` (or `$CODEX_HOME/hooks.json` when configured). Keep existing handlers in each event's list. If using another installation path, update the command consistently.

```json
{
  "hooks": {
    "SessionStart": [{"hooks": [{"type": "command", "command": "/usr/bin/python3 \"$HOME/.codex/hooks/codexccskill-guard/guard.py\"", "timeout": 5}]}],
    "UserPromptSubmit": [{"hooks": [{"type": "command", "command": "/usr/bin/python3 \"$HOME/.codex/hooks/codexccskill-guard/guard.py\"", "timeout": 5}]}],
    "PreToolUse": [{"matcher": "^(Bash|apply_patch|Agent|spawn_agent|mcp__.*)$", "hooks": [{"type": "command", "command": "/usr/bin/python3 \"$HOME/.codex/hooks/codexccskill-guard/guard.py\"", "timeout": 5}]}],
    "PostToolUse": [{"matcher": "^(Bash|apply_patch)$", "hooks": [{"type": "command", "command": "/usr/bin/python3 \"$HOME/.codex/hooks/codexccskill-guard/guard.py\"", "timeout": 5}]}],
    "Stop": [{"hooks": [{"type": "command", "command": "/usr/bin/python3 \"$HOME/.codex/hooks/codexccskill-guard/guard.py\"", "timeout": 5}]}],
    "Interrupt": [{"hooks": [{"type": "command", "command": "/usr/bin/python3 \"$HOME/.codex/hooks/codexccskill-guard/guard.py\"", "timeout": 2}]}]
  }
}
```

Review and trust the six hooks in **Settings → Hooks** in the desktop app or with `/hooks` in the CLI, then start or reopen a local conversation. [Codex Hooks documentation](https://learn.chatgpt.com/docs/hooks)

## Use the guard

Send requests normally. Read-only tasks can finish directly. For shell commands that change state, the guard instructs Codex to use `guard.py run <command>`. For final acceptance, it uses `guard.py verify <command>`. These helpers execute the command in the current tool environment. The guard also checks recorded file edits and verification exit codes when a supported local transcript is available. An edit after verification requires a fresh check.

For a narrower, explicitly defined write scope, put the following policy on the first line of the request:

```text
Guard policy {"write":["src/export.py","tests/"],"check":"python3 -m unittest"}
Fix the export through its normal entry point.
```

Use workspace-relative paths in `write` and end a directory with `/`. Set `check` to a single reviewed command to run from the workspace root. Exact-scope mode allows authorized patches, the declared check, and a limited set of read-only shell commands.

## Allow an exact file outside the workspace

In default mode, an administrator can put a local `external-updates.json` next to the installed guard. Keys are absolute workspace roots and values are lists of absolute paths to existing files.

```json
{"/path/to/workspace": ["/path/to/existing-plan.md"]}
```

The entry permits an in-place patch for that file in the named workspace. It grants no permission to remove or move the file, and exact-scope mode still follows its own path restrictions.

## Enforcement scope

The guard covers lifecycle events and supported tool and transcript paths. The host sandbox and permissions control access within shell commands, external services, and other tools. The skill and the project's acceptance checks determine whether the entire task is complete. Project-defined stop and retry rules still apply. [Codex tool coverage](https://learn.chatgpt.com/docs/hooks#tool-coverage)
