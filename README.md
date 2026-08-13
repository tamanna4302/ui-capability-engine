# Computer-Use Automation System

A small end-to-end computer-use automation system that demonstrates:

- LLM-driven UI discovery
- Reusable typed capability artifacts
- Deterministic replay without an LLM
- Runtime error classification and recovery
- Safety policy enforcement
- Human-in-the-loop control transfer
- Structured evidence and failure capture

The project uses a local mock banking application as a stand-in for a legacy back-office application with no API.

## How It Works

The system separates workflow discovery from production execution.

During discovery:

1. A natural-language goal is provided to the discovery agent.
2. Claude observes the live application through structured UI observations.
3. Claude chooses one action at a time, such as typing or clicking.
4. Once the goal is completed, the successful interaction is converted into a reusable capability artifact.
5. Invocation-specific values are replaced with parameters.

During replay:

1. The saved capability artifact is loaded.
2. New input parameters are supplied.
3. The recorded workflow is executed deterministically.
4. No LLM is used to decide replay actions.
5. Checkpoints are verified and declared outputs are returned.

Example:

```text
Discovery goal:
Look up member 12345 and return their current savings balance.

Claude:
Type 12345
→ Click Search
→ Observe Member Details
→ Complete with $4,231.44

Generated capability:
get_savings_balance(member_id)

Later replay:
member_id = 67890
→ deterministic execution
→ savings_balance = $823.19
```

## Project Structure

```text
.
├── capabilities/
│   └── get_savings_balance.v1.json
├── evidence/
│   ├── discovery/
│   ├── replay/
│   └── handoff/
├── mock_bank/
│   ├── app.py
│   └── templates/
├── src/
│   ├── agent/
│   ├── artifacts/
│   ├── escalation/
│   ├── models/
│   ├── observability/
│   ├── policy/
│   ├── replay/
│   └── surface/
├── tests/
├── run_discovery.py
├── run_replay.py
├── README.md
├── REPORT.md
└── requirements.txt
```

## Requirements

- Python 3.11+
- Playwright with Chromium
- Anthropic API key for LLM-driven discovery

Deterministic replay does not require an Anthropic API call.

## Setup

Install the dependencies:

```bash
python3 -m pip install -r requirements.txt
python3 -m playwright install chromium
```

Set the Anthropic API key before running discovery:

```bash
export ANTHROPIC_API_KEY="your_api_key_here"
```


## Start the Mock Application

Start the local banking application:

```bash
python3 mock_bank/app.py
```

The application runs at:

```text
http://127.0.0.1:5000/
```

The mock application contains synthetic member data and several behaviors used to demonstrate the automation system.

## Run Discovery

Keep the mock application running and open another terminal.

Run:

```bash
python3 run_discovery.py
```

A visible Chromium browser opens.

Claude receives structured observations of the application and independently chooses UI actions until the goal is completed or a stopping condition is reached.

A successful discovery creates:

```text
capabilities/get_savings_balance.v1.json
```

Discovery evidence is stored under:

```text
evidence/discovery/
```

The generated capability parameterizes the discovered member ID so the workflow can later be reused with different member IDs.

## Run Deterministic Replay

Run:

```bash
python3 run_replay.py
```

Replay:

- Loads the saved capability artifact
- Validates required inputs
- Applies policy checks
- Executes the recorded steps
- Resolves recorded UI targets
- Verifies checkpoints
- Extracts declared outputs
- Returns a structured result

The replay engine does not use the LLM to decide what action to perform.

Example successful result:

```text
{
    'status': 'success',
    'outputs': {
        'savings_balance': '$823.19'
    }
}
```

## Capability Artifact

The generated artifact is stored at:

```text
capabilities/get_savings_balance.v1.json
```

It contains:

- Schema version
- Capability name and version
- Description
- Target application
- Entry point
- Typed inputs
- Typed outputs
- Ordered steps
- UI targets and locator fallbacks
- Checkpoints
- Business outcomes
- Final success condition

For example, the member ID used during discovery is converted into the reusable parameter:

```text
member_id
```

instead of being hard-coded into replay.

## Locator Strategy

The system supports multiple target locator strategies:

- Accessibility role and accessible name
- Associated form label
- Visible text
- Semantic table-cell targeting
- CSS selectors as fallbacks

For the savings balance, the preferred locator identifies the value semantically:

```text
row = Savings
column = Current Balance
```

This avoids depending only on a specific row position in the page.

A CSS selector is retained as a fallback.

## Runtime Outcomes

The replay engine distinguishes between different types of runtime outcomes.

### Success

The workflow completed and returned its declared outputs.

### Business Outcome

A valid business result is not treated as an automation failure.

For example, an unknown member can return:

```text
{
    'status': 'business_outcome',
    'code': 'MEMBER_NOT_FOUND'
}
```

### Recoverable Condition

The mock application includes a transient service-error scenario.

Replay can recognize the temporary condition, restore the workflow to a known state, and retry within a bounded retry limit.

### Hard Failure

Failures such as an unresolved UI target return structured diagnostic information.

Example:

```text
{
    'status': 'hard_failure',
    'code': 'STEP_EXECUTION_FAILED',
    'step': 'step_2'
}
```

Replay stops rather than continuing from an unknown state.

## Safety

A `PolicyEngine` evaluates actions before replay executes them.

The policy layer supports:

- Allowed hosts
- Allowed action types
- Detection of potentially risky or irreversible actions

Normal read and search operations can proceed automatically.

Potentially risky actions are not automatically executed and can instead trigger human intervention.

Sensitive invocation inputs are redacted from structured evidence logs.

API credentials are not stored in capability artifacts.

## Human Handoff

The system supports transfer of control to a human while preserving the same live browser session.

When intervention is required:

1. Automation pauses.
2. The existing browser remains open.
3. The current state is captured.
4. The human operates the same browser session.
5. Manual interaction evidence is recorded.
6. The human returns control.
7. The expected checkpoint is verified.
8. Automation resumes.

Handoff evidence is stored under:

```text
evidence/handoff/
```

## Observability and Evidence

Evidence is organized under:

```text
evidence/
├── discovery/
├── replay/
└── handoff/
```

The project includes evidence of genuine LLM-driven discovery and deterministic replay.

Structured JSON logs record important run lifecycle information.

Failure runs can additionally capture screenshots to make failures easier to understand and debug.

Sensitive invocation inputs are redacted from structured logs.

## Tests

Run the automated tests with:

```bash
python3 -m pytest -v
```

Tests cover important behaviors including:

- Allowed navigation
- Blocked navigation
- Safe actions
- Risky actions requiring human intervention
- Successful deterministic replay
- Business outcomes
- Recoverable transient conditions
- Hard failures
- Required input validation

## Design Report

See `REPORT.md` for discussion of:

- Architecture
- Artifact schema
- Determinism and error handling
- Heterogeneity and multi-tenant considerations
- Escalation and handoff
- Safety
- Deliberate scope cuts