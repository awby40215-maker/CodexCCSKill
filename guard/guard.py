#!/usr/bin/env python3
"""Default Codex skill loading and tool checks for local conversations."""

import json
import os
import re
import shlex
import shutil
import sqlite3
import subprocess
import sys
from pathlib import Path
from secrets import token_hex
from urllib.parse import unquote, urlsplit


HEADER = "Guard policy "
VERIFY = "codexccguard verify "
RUN = "codexccguard run "
DATABASE = Path(__file__).with_name("turns.sqlite3")
EXTERNAL_UPDATES = Path(__file__).with_name("external-updates.json")
SKILL = Path.home() / ".agents" / "skills" / "codexccskill" / "SKILL.md"
COMPANION = str(Path(__file__).resolve())
PATCH_PATH = re.compile(r"^\*\*\* (Add File|Update File|Delete File|Move to): (.+)$", re.M)
READ_TOOLS = {
    "pwd": ("/bin/pwd", set()),
    "ls": ("/bin/ls", {"-a", "-l", "-la", "-al", "-h", "-lah", "-lahF"}),
    "cat": ("/bin/cat", {"-n", "-b"}),
    "head": ("/usr/bin/head", {"-n"}),
    "tail": ("/usr/bin/tail", {"-n"}),
    "rg": (None, {"--files", "-n", "-i", "-l", "-S", "-F", "--hidden", "--no-heading", "-g"}),
}


def path_from_hook(value):
    if value.startswith("file://"):
        url = urlsplit(value)
        if url.netloc not in ("", "localhost"):
            raise ValueError("The guard requires a local file path")
        value = unquote(url.path)
    path = Path(value)
    if not path.is_absolute():
        raise ValueError("Codex did not provide an absolute working directory")
    return path.resolve()


def authorized_paths(root, entries):
    paths = []
    if not isinstance(entries, list):
        raise ValueError("write must be a list of relative paths")
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip() or Path(entry).is_absolute():
            raise ValueError("write entries must be relative to the working directory")
        target = Path(os.path.abspath(root / entry))
        if target == root or not target.is_relative_to(root) or target != target.resolve():
            raise ValueError("write entries must name files or subdirectories inside the workspace")
        paths.append([str(target), entry.endswith("/")])
    return paths


def command_args(command):
    if not isinstance(command, str) or "\n" in command:
        raise ValueError("Provide a single verification command")
    argv = shlex.split(command)
    if not argv or any(arg in {"|", "||", "&", "&&", ";", ">", ">>", "<"} for arg in argv):
        raise ValueError("Use a single verification command such as python3 -m unittest")
    return argv


def new_state(event, header=""):
    root = path_from_hook(event["cwd"])
    write, check = None, None
    if header:
        policy = json.loads(header.removeprefix(HEADER))
        if not isinstance(policy, dict) or set(policy) != {"write", "check"}:
            raise ValueError("Guard policy requires write and check")
        write = authorized_paths(root, policy["write"])
        check = command_args(policy["check"])
    return {
        "root": str(root),
        "write": write,
        "check": check,
        "turn": event["turn_id"],
        "patches": [],
        "checks": {},
        "passed": False,
        "requires_verification": bool(header),
    }


def read_command(argv):
    tool, *args = argv
    if tool == "sed" and len(args) >= 3 and args[0] == "-n":
        if re.fullmatch(r"[1-9]\d*(?:,[1-9]\d*)?p", args[1]) and not any(
            arg.startswith("-") for arg in args[2:]
        ):
            return shlex.join(["/usr/bin/sed", *args])
    if tool not in READ_TOOLS:
        return None
    executable, flags = READ_TOOLS[tool]
    for arg in args:
        if arg == "--":
            break
        if arg.startswith("-") and arg not in flags:
            return None
    if tool in {"head", "tail"} and "-n" in args:
        index = args.index("-n") + 1
        if index == len(args) or not re.fullmatch(r"[1-9]\d*", args[index]):
            return None
    if tool == "pwd" and args:
        return None
    if tool == "rg":
        executable = shutil.which("rg")
        args = ["--no-config", *args]
    return shlex.join([executable, *args]) if executable else None


def deny(reason):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": reason,
        }
    }


def rewrite(command):
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "allow",
            "updatedInput": {"command": command},
        }
    }


def record_write(state, call):
    state["patches"].append(call)
    state["passed"] = False
    state.pop("proof", None)
    state["requires_verification"] = True


def verify_command(event, state, call, argv):
    reconcile_patches(event, state)
    if state["patches"]:
        return deny("Wait for the current edit to finish before verifying.")
    if state["checks"]:
        return deny("Wait for the current verification command to finish.")
    token = "CODEXCC_GUARD_OK_" + token_hex(16)
    state["checks"][call] = token
    state["passed"] = False
    state.pop("proof", None)
    state["requires_verification"] = True
    return rewrite(shlex.join(argv) + " && printf '\\n%s\\n' " + shlex.quote(token))


def external_update_allowed(root, target):
    try:
        catalog = json.loads(EXTERNAL_UPDATES.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return False
    paths = catalog.get(str(root), []) if isinstance(catalog, dict) else []
    return isinstance(paths, list) and str(target) in paths and target.is_file()


def patch_allowed(command, cwd, root, write):
    entries = PATCH_PATH.findall(command)
    if not entries or re.search(r"^\*\*\* Environment ID:", command, re.M):
        return False
    next_operations = [operation for operation, _ in entries[1:]] + [None]
    for (operation, name), next_operation in zip(entries, next_operations):
        target = Path(os.path.abspath(cwd / name))
        if target != target.resolve():
            return False
        if target.is_relative_to(root):
            if write is not None and not any(
                target == Path(allowed) or (tree and target.is_relative_to(allowed))
                for allowed, tree in write
            ):
                return False
            continue
        if (write is not None or operation != "Update File" or next_operation == "Move to"
                or not external_update_allowed(root, target)):
            return False
    return True


def before_tool(event, state):
    strict = state["write"] is not None
    if event.get("tool_name") not in {"Bash", "apply_patch"}:
        return deny("Exact-scope mode allows local edits and verification tools.") if strict else {}
    if event["tool_name"] == "apply_patch":
        state["requires_verification"] = True
    command = event["tool_input"]["command"]
    verify_prefix, run_prefix = VERIFY, RUN
    if event["tool_name"] == "Bash" and not strict:
        verify_prefix = next((prefix for prefix in (VERIFY, companion_text("verify") + " ")
                              if command.startswith(prefix)), VERIFY)
        run_prefix = next((prefix for prefix in (RUN, companion_text("run") + " ")
                           if command.startswith(prefix)), RUN)
    if event["tool_name"] == "Bash" and not strict and command.startswith((run_prefix, verify_prefix)):
        state["requires_verification"] = True
    cwd = path_from_hook(event["cwd"])
    root = Path(state["root"])
    if not cwd.is_relative_to(root):
        return deny("The tool working directory is outside the workspace for this turn.")
    call = event["tool_use_id"]
    if event["tool_name"] == "apply_patch":
        if not patch_allowed(command, cwd, root, state["write"]):
            return deny("The patch targets a path outside the guard policy.")
        if state["checks"]:
            return deny("Wait for verification to finish before editing files.")
        record_write(state, call)
        state.setdefault("patch_invocations", {})[call] = patch_invocation(event, call)
        return {}
    if not strict:
        if command.startswith(verify_prefix):
            return verify_command(event, state, call, command_args(command.removeprefix(verify_prefix)))
        if command.startswith(run_prefix):
            if state["checks"]:
                return deny("Wait for verification to finish before running a command that changes state.")
            approved_command = command.removeprefix(run_prefix).strip()
            if not approved_command:
                return deny("Provide the command to run.")
            record_write(state, call)
            return rewrite(approved_command if run_prefix == RUN else shlex.join(command_args(approved_command)))
        return {}
    try:
        argv = shlex.split(command)
    except ValueError:
        argv = []
    if argv == state["check"] and cwd == root:
        return verify_command(event, state, call, argv)
    safe_read = read_command(argv) if argv and not any(
        arg in {"|", "||", "&&", "&", ";", ">", ">>", "<"} for arg in argv
    ) else None
    if safe_read:
        return rewrite(safe_read)
    return deny(
        "Use apply_patch for allowed edits, use pwd, ls, cat, head, tail, rg, or sed -n for reads, "
        "and run the declared verification command by itself from the workspace root."
    )


def after_tool(event, state):
    call = event["tool_use_id"]
    if call in state["patches"]:
        state["patches"].remove(call)
        state.get("patch_invocations", {}).pop(call, None)
    token = state["checks"].pop(call, None)
    if token:
        output = event.get("tool_response")
        state["passed"] = isinstance(output, str) and output.rstrip().splitlines()[-1:] == [token]
        if state["passed"]:
            state["proof"] = token


def reverse_lines(file):
    offset = file.seek(0, os.SEEK_END)
    prefix = b""
    while offset:
        count = min(offset, 131072)
        offset -= count
        file.seek(offset)
        prefix, *lines = (file.read(count) + prefix).split(b"\n")
        yield from reversed(lines)
    yield prefix


def patch_transcript(event):
    path = event.get("transcript_path")
    if not path:
        return
    turn = event["turn_id"]
    try:
        with Path(path).open("rb") as file:
            for line in reverse_lines(file):
                if not any(marker in line for marker in (
                    b'"custom_tool_call"', b'"function_call"', b'"custom_tool_call_output"',
                    b'"function_call_output"', b'"task_started"', b'"FileChange"',
                )):
                    continue
                try:
                    row = json.loads(line)
                except (json.JSONDecodeError, UnicodeDecodeError):
                    continue
                payload = row["payload"]
                if row["type"] == "response_item":
                    yield payload
                elif row["type"] == "event_msg" and payload.get("turn_id") == turn:
                    if payload.get("type") == "task_started":
                        return
                    if payload.get("type") == "item_completed":
                        yield payload
    except OSError:
        return


def patch_invocation(event, call):
    completed = set()
    for entry in patch_transcript(event):
        kind, parent = entry.get("type"), entry.get("call_id")
        if kind in ("custom_tool_call_output", "function_call_output"):
            completed.add(parent)
        elif kind in ("custom_tool_call", "function_call"):
            name = entry.get("name")
            if (name == "apply_patch" and parent == call) or (kind == "custom_tool_call" and name == "exec"):
                return parent if parent not in completed else None
    return None


def reconcile_patches(event, state):
    tracked = state.get("patch_invocations", {})
    if not tracked:
        return
    for entry in patch_transcript(event):
        kind = entry.get("type")
        if kind == "item_completed":
            item = entry.get("item", {})
            finished = [item.get("id")] if item.get("type") == "FileChange" else []
        elif kind in ("custom_tool_call_output", "function_call_output"):
            parent = entry.get("call_id")
            # A rejected synchronous patch may only have an enclosing tool result.
            finished = [call for call, invocation in tracked.items() if parent and invocation == parent]
        else:
            continue
        for call in finished:
            if call in tracked:
                tracked.pop(call)
                state["patches"].remove(call)
        if not tracked:
            return


def companion_action(command):
    if not isinstance(command, list) or not command:
        return None
    argv = command
    if len(command) == 3 and command[1] in ("-c", "-lc"):
        try:
            argv = command_args(command[2])
        except ValueError:
            return None
    if len(argv) >= 4 and argv[:2] == ["/usr/bin/python3", COMPANION] and argv[2] in ("run", "verify"):
        return argv[2]
    return None


def transcript_evidence(event, state):
    path = event.get("transcript_path")
    if not path:
        return None, None
    turn = event["turn_id"]
    target = turn.encode()
    verified = None
    with Path(path).open("rb") as file:
        for line in reverse_lines(file):
            if target not in line or b'"event_msg"' not in line:
                continue
            try:
                payload = json.loads(line)["payload"]
            except json.JSONDecodeError:
                continue
            if payload.get("turn_id") != turn:
                continue
            if payload.get("type") == "task_started":
                break
            if payload.get("type") != "item_completed":
                continue
            item = payload.get("item", {})
            if item.get("type") == "FileChange":
                return bool(verified), item.get("id") if item.get("status") == "completed" else None
            if item.get("type") != "CommandExecution":
                continue
            action = companion_action(item.get("command"))
            if action == "run":
                return bool(verified), item.get("id") if item.get("exit_code") == 0 else None
            output = item.get("aggregated_output") or ""
            if verified is None and (action == "verify" or (
                state.get("proof") and output.rstrip().splitlines()[-1:] == [state["proof"]]
            )):
                verified = item.get("exit_code") == 0
    return verified, None


def companion_text(action):
    return shlex.join(["/usr/bin/python3", COMPANION, action])


def process(event, state, header):
    kind = event["hook_event_name"]
    if kind == "UserPromptSubmit":
        if header.startswith(HEADER):
            try:
                state = new_state(event, header)
            except (KeyError, ValueError) as exc:
                return None, {"decision": "block", "reason": f"Invalid guard policy: {exc}"}
            return state, {
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": (
                        f"Exact-scope guard is active. Follow CodexCCSKill and read {SKILL} if needed. "
                        "Use apply_patch for allowed edits and call read-only commands separately. "
                        "Run the following verification command from the workspace root: "
                        + shlex.join(state["check"])
                    ),
                }
            }
        if state and event.get("prompt") == state.get("continuation"):
            state["turn"] = event["turn_id"]
            return state, {}
        try:
            state = new_state(event)
        except (KeyError, OSError, ValueError):
            return None, {"systemMessage": "CodexCCSKill is loaded. The guard needs a local working directory."}
        return state, {
            "hookSpecificOutput": {
                "hookEventName": "UserPromptSubmit",
                "additionalContext": (
                    f"The CodexCCSKill guard is active. Follow the skill and read {SKILL} if needed. "
                    "Answer questions and read-only requests directly. Use apply_patch for file edits. "
                    f"For a single shell command that changes state, run {companion_text('run')} <command>. "
                    f"Use {companion_text('verify')} <acceptance command> for the final check after "
                    "reviewing every deliverable. Run partial checks through the normal project commands. "
                    "Continue while authorized steps remain and report concrete blockers. "
                    "Follow the project's stop and retry rules for formal runs."
                ),
            }
        }
    if not state or state["turn"] != event.get("turn_id"):
        return state, {}
    if kind == "PreToolUse":
        try:
            return state, before_tool(event, state)
        except (KeyError, OSError, ValueError, RuntimeError, TypeError):
            return state, deny("The guard could not confirm the operation's working directory, paths, or arguments.")
    if kind == "PostToolUse":
        after_tool(event, state)
    if kind == "Interrupt":
        return None, {}
    if kind == "Stop":
        reconcile_patches(event, state)
        progress = None
        if state["check"] is None:
            try:
                observed, progress = transcript_evidence(event, state)
            except OSError:
                observed = None
            if observed is not None:
                state["requires_verification"] = True
                state["passed"] = observed
        if not state.get("requires_verification", state["check"] is not None):
            return None, {}
        if state["passed"] and not state["patches"] and not state["checks"]:
            return None, {}
        continued = state.get("continuation") or event.get("stop_hook_active")
        if continued and (not progress or progress == state.get("continuation_progress")):
            return None, {
                "systemMessage": "Acceptance is still pending and the continuation showed no new verifiable edits. "
                "Review the remaining acceptance criteria."
            }
        command = shlex.join(state["check"]) if state["check"] else companion_text("verify") + " <acceptance command>"
        reason = (
            "The guard has no passing final verification. Recheck the user's acceptance criteria "
            f"and continue any remaining authorized work. Run {command} as the final check. "
            "Honor user and project stop conditions and report concrete blockers."
        )
        state["continuation"] = reason
        state["continuation_progress"] = progress
        return state, {"decision": "block", "reason": reason}
    return state, {}


def main(database):
    event = json.load(sys.stdin)
    if event["hook_event_name"] == "SessionStart":
        body = SKILL.read_text(encoding="utf-8").split("---\n", 2)[-1].strip()
        print(json.dumps({
            "hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": body},
        }, ensure_ascii=False))
        return
    prompt = event.get("prompt", "")
    header = prompt.partition("\n")[0].rstrip()
    if not database.exists() and event["hook_event_name"] != "UserPromptSubmit":
        print("{}")
        return
    with sqlite3.connect(database, timeout=2) as connection:
        connection.execute("CREATE TABLE IF NOT EXISTS turns (session TEXT PRIMARY KEY, state TEXT)")
        connection.execute("BEGIN IMMEDIATE")
        session = event["session_id"]
        row = connection.execute("SELECT state FROM turns WHERE session = ?", (session,)).fetchone()
        state, result = process(event, json.loads(row[0]) if row else None, header)
        if state is None:
            if row:
                connection.execute("DELETE FROM turns WHERE session = ?", (session,))
        elif not row or json.loads(row[0]) != state:
            connection.execute("INSERT OR REPLACE INTO turns VALUES (?, ?)", (session, json.dumps(state)))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] in ("run", "verify"):
        if len(sys.argv) < 3:
            raise SystemExit("Provide the command required for the current task")
        raise SystemExit(subprocess.run(sys.argv[2:], check=False).returncode)
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DATABASE)
