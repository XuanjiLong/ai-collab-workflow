# Dispatch / Invoke Mechanism

In this repo, “Invoke Coder / Invoke Reviewer” is an abstract action: the Main Agent must send standardized context (TaskContract, etc.) to a role-specific agent and receive a JSON artifact back.

This playbook does not mandate an implementation (role switching, subprocess, API calls, multi-session). But you must implement **a dispatcher interface**, **prompt assembly conventions**, and **context isolation rules** to make the protocol reliable.

### 1) Dispatcher Interface (Recommended)

Implement “Invoke” as a minimal interface:

- `dispatch(role, system_prompt, user_input) -> raw_output_text`
- `raw_output_text` MUST be parseable as protocol JSON (no extra prose).

Persist each call’s input/output as artifacts to support retries and auditing.

### 2) Recommended Dispatch Patterns

#### A. Multi-session (Recommended)

Main / Coder / Reviewer run in isolated sessions (or isolated sub-agents), each with its own system prompt.

Best when:
- You can run multiple terminals/sessions
- You care about review independence (avoid context leakage)

#### B. Subprocess or API Calls (Automation)

A Main orchestrator (or a thin script) executes role-specific LLM calls and writes stdout directly to `coder_output.json` / `review_result.json`.

Best when:
- High throughput
- You want deterministic, scriptable I/O

#### C. Single-session Role Switching (Not recommended)

One session “acts as Coder” then “acts as Reviewer”.

Use only for quick demos because the reviewer is likely biased by prior context.

### 3) Prompt Assembly Conventions

#### Coder

- System prompt: `docs/prompts/coder.prompt.md`
- User input: inject full TaskContract JSON

```text
You are the Coder agent. Return ONLY raw JSON, starting with '{' and ending with '}'.

TASK_CONTRACT_JSON:
{{TASK_CONTRACT_JSON}}
```

#### Reviewer

- System prompt: `docs/prompts/reviewer.prompt.md`
- User input: inject TaskContract + coder_output JSON

```text
You are the Reviewer agent. Return ONLY raw JSON, starting with '{' and ending with '}'.

TASK_CONTRACT_JSON:
{{TASK_CONTRACT_JSON}}

CODER_OUTPUT_JSON:
{{CODER_OUTPUT_JSON}}
```

### 4) Context Isolation Rules

Coder SHOULD see:
- Current `TaskContract` (including `rework.previous_review_result.block_issues` on retries)
- Necessary repo facts (paths/snippets/constraints)

Coder SHOULD NOT see:
- Reviewer system prompt
- Main’s decision logic internals

Reviewer SHOULD see:
- Current `TaskContract`
- Current `coder_output` (including patch + self_review)

Reviewer SHOULD NOT see:
- Main’s final decision preference
- Unrelated chat history (avoid bias)

Recommendation:
- Score independently first, then read coder self-review to compute alignment deltas (avoid anchoring).

### 5) Receiving + Validating Outputs

Main Agent must validate:
- Schema (structure)
- Semantics (math + cross-file consistency)

Example strict validation for a single `review_result`:

```bash
python scripts/validate_artifact.py \
  --schema schemas/review_result.schema.json \
  --input .workflow/tasks/T-.../round-2/review_result.json \
  --task-contract .workflow/tasks/T-.../round-2/task_contract.json \
  --coder-output .workflow/tasks/T-.../round-2/coder_output.json \
  --strict
```

If JSON parsing or validation fails:
- Do not advance the state machine
- Persist the failed artifact
- Ask the role agent to regenerate with the same input (re-emphasize “ONLY raw JSON”)

### 6) CLI Integration Examples

These are implementable integration shapes that do not depend on vendor-specific flags.

#### 6.1 Minimal: 3 terminals (universal)

Run three isolated sessions (Main/Coder/Reviewer) with role prompts, and pass artifacts between them via copy/paste or files.

#### 6.2 Automated: Scripted dispatcher (pseudocode)

Map `llm_call` to your tool’s single-call capability (system prompt + user message -> stdout), then validate and persist artifacts.
