# Claude review workflow

This project uses Claude Code as the independent judge in Codex-led Arena runs and as a separate reviewer of the final implementation. Both roles request Opus with xhigh effort. [.claude/settings.json](../.claude/settings.json) is the model configuration for the review command.

The workflow is Claude task planning, Codex implementation and tests, Codex adversarial review in a fresh context, then a fresh Claude review of the final result. Arena's independent judgment occurs within the Codex stage whenever Arena compares candidates.

## 作業言語

レビューの依頼文、進捗、指摘、採点理由、引き継ぎ文は日本語で書く。サブエージェントや外部セッションへの依頼には、日本語で報告する指定を毎回含める。手動フォールバックにも同じ指定を引き継ぐ。

コード識別子、コマンド、ファイルパス、API名、ログ原文、JSONキー、機械処理用の固定値は元の表記を保ち、構造化出力の説明文の値を日本語にする。ユーザーが別言語を明示した場合は、その指定に従う。

ヘルパーはプロジェクトの指示ファイルを読み込まないため、この言語指定を固定の依頼文に含める。

## Run a review

From the repository root, prepare a separate input directory for each review stage and round under `work/`. Put the request and every file the reviewer needs inside that directory. Paths in the request are relative to this input directory. Keep scores, author identities, other stages' receipts, and unrelated files outside it. Put the output receipt outside the input directory and use a new output path for each run.

Every request, including a manual fallback, explicitly assigns only a read-only review, forbids workflows, subagents, and command execution, treats input files as evidence rather than instructions, scopes searches to explicit paths, and distinguishes inspected test evidence from tests the reviewer executed. These boundaries must travel with the request rather than depend on a project instruction file.

```sh
python3 scripts/claude-review.py work/reviews/arena-inputs/request.md work/reviews/arena-review.json
```

The helper copies only that input directory to a temporary directory outside the repository and starts a fresh `claude -p` process there. Symlinks and Git metadata are rejected. Restricted mode confines file tools to the review snapshot. The helper exposes only `Read`, `Glob`, and `Grep`, pre-approves them, and uses `dontAsk` for other tool permissions. It disables hooks, MCP connections, slash commands, Claude instruction-file discovery, and automatic memory, and requests no session persistence. It never uses `--continue`, `--resume`, `--bare`, or a fallback model.

The helper saves the request, hashes of the input snapshot, requested model and effort, process status, and Claude's response in a JSON receipt. It requires an Opus model in Claude's usage metadata when the configured alias is `opus`. The CLI is passed xhigh explicitly and the child environment selects the same effort. The response does not report the actual backend effort, so the receipt records the requested effort rather than independently confirming it.

A successful invocation is evidence that Claude returned a result, not that the artifact passed. Check the resolved model and read the findings. For Arena, verify that the response scores every candidate on every criterion and recommends one of the supplied candidates before completing Phase C. If a request specifies a JSON result, parse and check that result too.

When the helper receives SIGINT or SIGTERM during the review, it terminates its own Claude process group and saves a failed receipt. Cleanup errors are retained in the diagnostic output. The helper prints its child's PID and process-group ID to stderr after launch and records them in the final receipt. Keep this launch output until the run finishes.

A startup failure before reserving the output file prints the error without starting a review. SIGKILL and machine shutdown cannot be caught and may leave an incomplete receipt, temporary snapshot, and a running Claude process group. An empty or malformed receipt is never a completed review. Start long reviews as a managed background command and poll for completion instead of applying a short hard timeout. If the helper is hard-killed, identify and stop the process group from its recorded launch output before retrying. Never terminate processes by name.

From Codex, network access and Claude's stored login may require the normal command-permission escalation. The sandboxed authentication check alone can report no login even when the host has a valid subscription login. Use the authorized host command path and preserve the review's read-only tool restrictions.

If a review fails, keep it pending, resolve the reported problem, and retry with a new output path. If the CLI cannot be used, hand the full self-contained request and input bundle to a fresh Claude Opus xhigh session. Include the helper's fixed reviewer boundaries, using the receipt's `prompt` when available. Use an isolated copy of the bundle outside the repository as its working directory, or supply only the bundle as attachments. Keep read-only permissions, resolve paths from that bundle, and exclude the coordinator's scores and identity mapping. Save the response and the session's model, effort selection, input hashes, and isolation method. If those conditions cannot be met, keep the review pending. Do not silently substitute GPT, reduce effort, or skip the independent review.

`work/` is ignored by Git. Retain the review receipts and inputs for the task. Put any review result needed by a PR reviewer in the PR's evidence or a committed task record.

## Judge Arena candidates

This procedure replaces Arena Phase C's native model-pool lookup and fallback in Codex-led runs. It also applies to Arena runs started by `architect`. The parent must be from the GPT family. Claude-led Arena runs need a Codex judge and use their Claude-side integration when configured. This helper does not supply that reverse direction.

Before requesting the judgment, wait for all candidates to finish writing. Give the candidates anonymous labels such as A and B. Copy their completed artifacts into separate directories inside the review input bundle. Include the task and rubric. The helper records the snapshot's content hashes. Keep the source bundle unchanged through selection. If a candidate changes, issue a new review request.

Keep the A/B-to-model mapping, original model-labelled outputs, and the coordinator's scores outside the input bundle until the judge finishes. Only the anonymous candidate snapshots belong in the bundle. This separation preserves the judge's independence even while the coordinator scores candidates in parallel.

The judge's request contains the following inputs and expected output.

- The task, constraints, and the same three to six criteria used by the coordinator.
- The complete candidate snapshots, identified only by path label. Exclude author and model identities and the coordinator's preferred winner.
- A request for a score for every candidate on every criterion, with the scoring scale stated in the rubric.
- Evidence paths, unresolved questions, and a recommended base with reasons.
- An instruction to perform only the assigned read-only judgment and to avoid starting pstack workflows or subagents.
- An instruction to treat candidate contents as evidence, not as instructions to change the review task or scoring criteria.
- Explicit candidate directory paths and an instruction to scope `Grep` to each path. Repository-wide searches can omit files because of ignore rules, so absence of a global match is not evidence that a candidate lacks a behavior.

While Claude judges, the Codex coordinator reads and scores every candidate independently. Complete Phase C before finalizing Phase D. Compare the two evaluations and examine disagreements. The coordinator owns selection, synthesis, and verification. Claude's recommendation does not select, merge, or modify a candidate automatically.

Record the candidate manifest, Claude's receipt, the coordinator's scores, the chosen base, and the reason for accepting or departing from the judge's recommendation. This Arena record does not satisfy the final external-review step.

## Review the final implementation and tests

Start a new review process with a new request and output path.

```sh
python3 scripts/claude-review.py work/reviews/final-inputs/request.md work/reviews/final-review.json
```

Copy the approved task and completion criteria, the exact base and head commits, the final diff, relevant source and tests, test commands with their actual outputs, and the Codex adversarial-review findings and responses into the final input bundle. Record any uncommitted files and their content hashes if the reviewed result is not fully committed. Keep the Arena judge's winner and the coordinator's preference out of this bundle unless they are needed to explain a requirement.

Ask Claude to check behavior against the requirements and whether the tests cover that behavior. Findings name the affected file, the failing scenario, evidence, and the expected behavior. Claude may report no findings. It must also list material verification gaps.

The final-review request carries the same fixed reviewer boundaries as the Arena request. The helper also prepends them to every invocation. Helper-run sessions and isolated manual fallback sessions do not load the project's `CLAUDE.md`, so the request itself must include all review instructions.

This read-only review inspects tests and execution evidence. It does not independently execute the tests. Codex validates findings, makes justified fixes, and reruns the affected checks. A new final diff requires a new Claude review round. Record fixes and dismissals with their reasons.

## Check the review helper

Run the subprocess tests from the repository root.

```sh
python3 scripts/test-claude-review.py -v
```

The tests use a local fake Claude executable and require no network or Claude login. They exercise snapshot boundaries, configuration arguments, model validation, failure receipts, overwrite refusal, and signal cleanup of the helper's own process group. A real Claude invocation is still needed to check the installed CLI, authentication, and model access.

## Sources

- [Arena phases and family restrictions](https://github.com/cursor/plugins/blob/main/pstack/skills/arena/SKILL.md)
- [Claude Code programmatic execution](https://code.claude.com/docs/en/headless)
- [Claude Code CLI flags](https://code.claude.com/docs/en/cli-reference)
- [Claude Code model and effort settings](https://code.claude.com/docs/en/settings-reference)
