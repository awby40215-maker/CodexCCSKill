# CodexCCSKill

CodexCCSKill is a standalone Codex Agent Skill for implementation, debugging, verification, and resuming unfinished work. It adapts Claude Code's documented execution loop and Ponytail `full` to keep changes small and carry the task through the actual acceptance criteria.

## Install and use

Copy the entire `codexccskill` directory into `~/.agents/skills/` for personal use or `.agents/skills/` in a repository for team use. Keep the directory name. Invoke it with `$codexccskill`. [Codex skills documentation](https://developers.openai.com/codex/skills)

> Use $codexccskill to fix the broken export. Trace the normal entry point and verify that the actual consumer can read the resulting file.

The skill guides model decisions. The host controls permissions and enforcement.

## Distribute

Distribute the complete `codexccskill/` directory or a ZIP containing it. `SKILL.md` is the entry point. `agents/openai.yaml` provides the display name and suggested prompt. Preserve `LICENSE` with the distributed files.

## Credits and license

- Execution, planning, verification, and resumption adapted from Claude Code's public documentation. [How Claude Code works](https://code.claude.com/docs/en/how-claude-code-works) · [Common workflows](https://code.claude.com/docs/en/common-workflows) · [Best practices](https://code.claude.com/docs/en/best-practices)
- The minimal-change approach adapts DietrichGebert's Ponytail `full`. [Ponytail source](https://github.com/DietrichGebert/ponytail/blob/ebd8654c2c627f721eb8f9c0d1bd4090a29f9e10/skills/ponytail/SKILL.md)
- Released under the MIT License. [LICENSE](LICENSE)
