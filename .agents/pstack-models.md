# pstack model configuration

This file contains the approved native Codex model assignments for this repository.
The model names and reasoning effort are separate values in Codex.

```text
# budget: unlimited (max)
# reasoning_effort: max
feature, refactoring: gpt-6.1-sol
bug-fix: gpt-6.1-sol
perf-issue: gpt-6.1-sol
hillclimb: gpt-6.1-sol
judgment and prose: gpt-6-astra
hardest tasks: gpt-6-astra
how explorer: gpt-6.1-sol
how explainer: gpt-6-astra
why investigators: gpt-6.1-sol
why synthesizer: gpt-6-astra
reflect tooling: gpt-6.1-sol
reflect judgment, divergent, synthesizer: gpt-6-astra
arena runners: gpt-6-astra, gpt-6.1-sol
swarm workers: gpt-6.1-sol
architect runners: gpt-6-astra, gpt-6.1-sol
interrogate reviewers: gpt-6-astra, gpt-6.1-sol
```

Every real model entry uses `reasoning_effort: "max"` when spawned, including panel entries. The `unlimited` label selects reasoning effort, not the number of agents or concurrent tasks.

The `arena runners`, `architect runners`, and `interrogate reviewers` lists each contain two entries, so each panel starts two agents.

`swarm workers` supplies the default model for workers unless the skill assigns a model to a specific race or comparison arm.

Available model names confirmed for the setup session on 2026-10-31: `gpt-6.1-sol`, `gpt-6-astra`, `gpt-6.1-terra`, `gpt-6-sol`, and `gpt-6-luna`. Recheck availability in each new session. The aliases `inherit-parent` and `auto` inherit the parent settings.

## External Claude reviews

Arena's independent judge runs through the Claude Code CLI, as specified in [claude-review.md](claude-review.md). The native `arena cross-judge pool` row is intentionally omitted. The project routing overrides Arena's native pool and default fallback for Codex-led runs.

Both Arena Phase C and the final external review use the model and effort in [the Claude project settings](../.claude/settings.json). The approved values are model alias `opus` and effort `xhigh`. These are Claude Code arguments, not model names accepted by `collaboration.spawn_agent`.

The Codex assignments above remain at `max`. The Claude review sessions use `xhigh` and start with separate contexts.
