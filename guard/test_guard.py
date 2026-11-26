import json
import tempfile
import unittest
from pathlib import Path

from guard import HEADER, companion_text, process


class GuardVerificationTest(unittest.TestCase):
    def setUp(self):
        workspace = tempfile.TemporaryDirectory()
        self.addCleanup(workspace.cleanup)
        self.transcript = Path(workspace.name) / "transcript.jsonl"
        self.event = {
            "cwd": workspace.name,
            "turn_id": "current-turn",
            "transcript_path": str(self.transcript),
        }
        self.state = None
        self.record("event_msg", "task_started", turn_id="current-turn")

    def record(self, category, kind, **fields):
        row = {"type": category, "payload": {"type": kind, **fields}}
        with self.transcript.open("a", encoding="utf-8") as file:
            file.write(json.dumps(row) + "\n")

    def hook(self, kind, header="", **fields):
        self.state, result = process({**self.event, "hook_event_name": kind, **fields}, self.state, header)
        return result

    def tool(self, name, call, command):
        return self.hook("PreToolUse", tool_name=name, tool_use_id=call, tool_input={"command": command})

    def patch(self, call):
        return self.tool("apply_patch", call, "*** Begin Patch\n*** Add File: a.txt\n+example\n*** End Patch")

    def verification_decision(self, command):
        result = self.tool("Bash", "verify", command)
        return result["hookSpecificOutput"]["permissionDecision"]

    def test_failed_nested_patch_unblocks_only_after_its_parent_returns(self):
        self.hook("UserPromptSubmit")
        self.record("response_item", "custom_tool_call", name="exec", call_id="parent")
        self.assertEqual(self.patch("patch"), {})
        self.record("response_item", "custom_tool_call_output", call_id="another-call", output="Done")
        verify = companion_text("verify") + " /usr/bin/true"
        self.assertEqual(self.verification_decision(verify), "deny")

        self.record("response_item", "custom_tool_call_output", call_id="parent", output="Patch rejected")
        self.assertEqual(self.verification_decision(verify), "allow")
        self.assertFalse(self.state["passed"])
        self.assertTrue(self.state["requires_verification"])

    def test_exact_scope_uses_completed_file_change_when_callback_is_missing(self):
        self.hook("UserPromptSubmit", HEADER + '{"write":["a.txt"],"check":"/usr/bin/true"}')
        self.assertEqual(self.patch("patch"), {})
        self.record("event_msg", "item_completed", turn_id="another-turn", item={"type": "FileChange", "id": "patch"})
        self.assertEqual(self.verification_decision("/usr/bin/true"), "deny")
        self.record("event_msg", "item_completed", turn_id="current-turn", item={"type": "FileChange", "id": "patch"})
        self.assertEqual(self.verification_decision("/usr/bin/true"), "allow")

    def test_pending_shell_write_still_blocks_verification(self):
        self.hook("UserPromptSubmit")
        self.record("response_item", "custom_tool_call", name="exec", call_id="parent")
        run = companion_text("run") + " /usr/bin/true"
        self.tool("Bash", "shell", run)
        self.assertEqual(self.patch("patch"), {})
        self.record("response_item", "custom_tool_call_output", call_id="parent", output="Done")
        verify = companion_text("verify") + " /usr/bin/true"
        self.assertEqual(self.verification_decision(verify), "deny")
        self.assertEqual(self.state["patches"], ["shell"])

        self.hook("PostToolUse", tool_use_id="shell")
        self.assertEqual(self.verification_decision(verify), "allow")


if __name__ == "__main__":
    unittest.main()
