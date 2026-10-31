# Project instructions

## 作業言語

- メインセッションとサブエージェントの作業説明、進捗、調査結果、レビュー、引き継ぎ文は日本語で書く。
- サブエージェントへの依頼文、追加依頼、外部のClaudeやCodexへの委譲も日本語で書き、日本語で報告する指定を毎回明記する。
- コード識別子、コマンド、ファイルパス、API名、ログ原文、JSONキー、機械処理用の固定値は元の表記を保つ。構造化出力の説明文の値は日本語にする。
- pstackの英語テンプレートより、このプロジェクトの言語指定を優先する。ユーザーが別言語を明示した場合は、その指定に従う。

## pstack in Codex

- When using a pstack skill, read [.agents/pstack-models.md](.agents/pstack-models.md) for this project's role assignments. These assignments override the skill's model defaults.
- Pass each model name unchanged. Pass the configured effort through the tool's separate reasoning-effort argument.
- With `collaboration.spawn_agent`, use `model` and `reasoning_effort`. Explicit overrides require `fork_turns: "none"`, so include the needed context in the task message.
- For `inherit-parent` and `auto`, omit both model and reasoning-effort overrides.
- Check that the selected model and effort are available in the current session. If either is unavailable, report the mismatch before substituting another setting.
- Follow the skill's panel counts and cross-judge family restrictions. Treat all `gpt-*` models as one family for this project.
- For Codex-led `arena` runs, including those started by `architect`, use [.agents/claude-review.md](.agents/claude-review.md) for Phase C. A fresh Claude Code session supplies the independent judge. This project routing overrides the skill's native cross-judge pool and fallback logic.
- Complete the Claude judgment before finalizing Phase D's selection. If the judge cannot run, retain the review as pending and prepare a handoff for Claude. Do not replace it with another GPT model or report an independent judgment as complete.

These settings govern pstack subagent assignments in this repository. They do not change the parent chat's model or reasoning effort.

## Task workflow

Claude prepares the task scope, completion criteria, and verification requirements. Codex implements the task, runs tests, and conducts an adversarial review in a fresh context. A separate fresh Claude session then reviews the final implementation and test evidence. Keep this final external review separate from Arena Phase C's candidate comparison.

When preparing a handoff, include the applicable pstack skill at the beginning of the task prompt. Name any additional required skills, their purpose, and when to apply them.
