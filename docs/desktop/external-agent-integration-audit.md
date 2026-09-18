# External Agent Integration Audit

Date: 2026-09-18

This audit compares the locally available command-line agents for the first
Desktop External Agent integration. It intentionally does not rank agents or
define a provider abstraction. The current contract is Level 2 Capture /
Import and Replay / Evaluation interoperability; it is not an interactive
External Agent hosting contract.

## Codex CLI

- Stable interface: `codex exec`; the installed CLI also exposes `--version`.
- Working directory: `--cd <DIR>`.
- Non-interactive execution: yes, `codex exec [PROMPT]`.
- Structured/streaming output: `--json` emits JSONL events on stdout.
- Tool/activity events: JSONL includes activity events when the CLI emits them;
  the adapter preserves them as raw external events and does not invent AgentLab
  tool spans.
- Token/cost/model: model can be selected with `--model`; token and cost facts
  are not assumed unless a stable event supplies them.
- Exit/cancellation: process exit code is available; the child can be
  terminated by the Desktop process owner.
- Authentication: inherited from the user's Codex CLI configuration. AgentLab
  does not copy or manage credentials.
- Desktop child process: suitable; no daemon is required for `exec`.
- Additional server: not required.

## Claude Code

- Stable interface: `claude -p/--print` is available.
- Working directory: can be inherited from the child process; `--add-dir`
  changes allowed directories but is not the same as a single cwd contract.
- Non-interactive execution: yes.
- Structured/streaming output: print mode is available, but the minimum local
  contract is less direct than Codex's explicit JSONL mode.
- Tool/activity events: available through Claude-specific output options, but
  the adapter would need to select and maintain that protocol.
- Token/cost/model: not assumed by this audit.
- Exit/cancellation: ordinary child-process exit and termination semantics.
- Authentication: inherited from Claude Code; AgentLab does not manage it.
- Desktop child process: possible, but with more permission/authentication
  policy surface for this milestone.
- Additional server: not required.

## Pi

The `pi` executable was not installed on the audit machine, so no local CLI
contract was available to validate. AgentLab will not install it or infer its
runtime behavior.

## OpenCode

The `opencode` executable was not installed on the audit machine, so no local
CLI contract was available to validate. AgentLab will not install it or infer
its runtime behavior.

## v0.3 selection and boundary

Codex is the single external executor for v0.3 Replay / Evaluation. The choice
is based on the least
engineering resistance in this environment: it is installed, has an explicit
non-interactive command, accepts a canonical working directory, and exposes a
JSONL stream. The first adapter records output, status, exit code, and raw
external event summaries only. It leaves unavailable token/cost/model facts
unset rather than estimating them.

Codex does not appear as an interactive New Session executor. AgentLab Desktop
does not reproduce Codex conversation/session, resume, approval, permission,
sandbox, or provider-specific model UX. Cross-Agent Replay remains a supported
engineering capability because Cases, Datasets, Runs, Evaluation, and Compare
assets must remain useful when an execution component changes.
