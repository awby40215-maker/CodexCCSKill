# CodexCCSKill

CodexCCSKill is an MIT-licensed Agent Skill that helps Codex finish what the user asked for, with the smallest complete change and evidence from the actual workflow. It works as a standalone skill. An optional local guard adds automatic loading and lifecycle checks.

## What it helps you do

| Problem | How CodexCCSKill helps |
| --- | --- |
| Work stops after a partial fix | Define observable acceptance conditions, exercise the normal entry point, and continue while authorized work remains. |
| A small request grows into extra work | Require every addition to serve a current requirement, an affected contract, or an evidenced failure. Reuse existing code and checks first. |
| A task resumes with stale context | Reconcile the current files and evidence, then resume at the first unfinished or invalidated step. |
| A local edit goes out of scope | The optional guard can reject supported patch targets outside the allowed scope and ask Codex to continue when a tracked edit has no passing final check. |

## Quick start

Download this repository using **Code → Download ZIP** or clone it. Copy the included `codexccskill` directory to `~/.agents/skills/` for personal use or to `.agents/skills/` in a project. Then give Codex a task such as:

> Use $codexccskill to fix this export and verify that the downstream reader can open the result.

The standalone skill needs no additional runtime. To enable the optional macOS guard, follow the [guard installation instructions](guard/README.md). The guard complements Codex permissions and project checks. Its enforcement depends on the host's tool coverage and the acceptance evidence it can observe.

## Credits

The workflow adapts the public [Claude Code execution loop](https://code.claude.com/docs/en/how-claude-code-works) and the [Ponytail full](https://github.com/DietrichGebert/ponytail/blob/ebd8654c2c627f721eb8f9c0d1bd4090a29f9e10/skills/ponytail/SKILL.md) approach to minimal changes. The skill runs in Codex independently of Claude Code.

[MIT License](LICENSE)
