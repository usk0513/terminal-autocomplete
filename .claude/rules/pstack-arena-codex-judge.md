# pstack arena cross-judge: run it on Codex

In Claude Code every `Agent` subagent is a Claude model, so the arena skill's Phase C rule (the judge is never from the parent's family) can never be met with a subagent. In this project, run the arena cross-judge on Codex through the Codex plugin instead. This overrides the `arena cross-judge pool` line in `pstack-models.md`. It applies only to the arena judge, not to any other pstack role.

## Model

- Default: `gpt-6.1-sol` with effort `xhigh`.
- Use `gpt-6-astra` with effort `xhigh` only for a hard judgment: the candidates differ mainly in subtle correctness or design trade-offs rather than surface quality, the arena covers more than one design direction, or a rubric criterion needs deep reasoning (concurrency, security, invariants, data loss).
- Effort stays `xhigh` because the plugin rejects `max` (openai/codex-plugin-cc#751). Switch both to `max` once the installed plugin accepts it.

## How to run it

1. After every Phase B candidate has finished writing, use the Write tool to put the judge prompt in a file next to the arena outputs, such as `/tmp/arena-<slug>/judge-prompt.md`. The prompt holds the task, the rubric, and each candidate's label with its absolute path. It tells Codex to read only and change nothing, to score every candidate on every criterion, and to recommend one base with its rationale.
2. Run the judge as one bare Bash command with `run_in_background: true`, so it runs while you read the candidates in Phase D:

   `node "<home>/.claude/plugins/cache/openai-codex/codex/1.0.6/scripts/codex-companion.mjs" task --fresh --model gpt-6.1-sol --effort xhigh --prompt-file /tmp/arena-<slug>/judge-prompt.md`

   Write `<home>` as the absolute home directory, not `~` or `$HOME`, and keep the quotes, so the call text matches the user's `sandbox.excludedCommands` entry in `~/.claude/settings.json`. Never add `--write`. Never pipe, chain, redirect or `cd` around this command: anything but the bare command runs sandboxed and fails with EPERM.
3. If the run fails with EPERM on `~/.claude/plugins`, the user's settings lack that sandbox exclusion: tell the user. If it fails for any other reason not caused by the prompt (an auth, network or model error), try the other model once. If nothing runs, skip the judge, pick the base alone in Phase D, and say so in the synthesis note with the error.
4. In the synthesis note, name the judge as Codex with the model and effort used.

## Upkeep

The command path pins the Codex plugin version `1.0.6`. After the plugin updates, change the path here and in `sandbox.excludedCommands` in `~/.claude/settings.json`.
