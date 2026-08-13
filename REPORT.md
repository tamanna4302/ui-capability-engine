# 1. Architecture

The system separates LLM-driven workflow discovery from deterministic production execution.

During discovery, an LLM operates a live application through a `Surface` abstraction. The surface exposes structured observations of the current UI and operations such as typing, clicking, reading text, and capturing screenshots.

The discovery loop follows:

```text
observe → decide → act → observe
```

Claude receives the natural-language goal and the current structured observation of the application. It chooses one UI action at a time until the goal is completed or a stopping condition is reached.

After a successful discovery run, an `ArtifactBuilder` converts the discovered interaction into a typed capability artifact. Invocation-specific values are replaced with reusable parameters.

Production execution uses a separate `ReplayEngine`. The replay engine loads the saved artifact and executes its steps directly without asking an LLM what action to perform.

The central architectural boundary is therefore:

```text
LLM-driven discovery
        ↓
typed capability artifact
        ↓
deterministic replay
```

The browser implementation is isolated behind the `Surface` abstraction. The current implementation uses Playwright, while the discovery and replay layers operate on higher-level actions and targets.

Additional components provide policy enforcement, human handoff, error recovery, and evidence capture.

I intentionally kept the implementation single-process and focused on one complete vertical slice rather than adding distributed workers, queues, databases, or other infrastructure that was unnecessary to demonstrate the core design.

# 2. Artifact schema

The capability artifact is a typed, versioned, human-reviewable representation of a reusable workflow.

It contains:

- Schema version
- Capability name and version
- Description
- Target application
- Entry point
- Typed inputs
- Typed outputs
- Ordered execution steps
- UI targets
- Locator fallbacks
- Checkpoints
- Business outcomes
- Final success condition
- Metadata

The artifact stores the reusable meaning of the discovered workflow rather than simply saving a transcript of the discovery conversation.

For example, discovery is performed using a concrete member ID such as `12345`. The generated artifact replaces that value with:

```text
parameter = member_id
```

The same artifact can therefore later be invoked with a different value such as `67890`.

Targets are also represented independently of the browser implementation.

The system supports semantic locator strategies such as roles, labels, text, and table semantics, with CSS available as a fallback.

For savings-balance extraction, the preferred target is represented as:

```text
row_text = Savings
column_header = Current Balance
```

rather than depending only on the balance being located in a particular numbered row.

This makes the artifact easier to review and more resilient to minor UI changes.

# 3. Determinism & error handling

Replay does not invoke the LLM to decide what action to perform.

Given the same capability artifact and inputs, the replay engine follows the artifact's ordered execution steps directly.

Replay includes:

- Required-input validation
- Recorded target resolution
- Locator fallbacks
- Per-step checkpoint verification
- Output extraction
- Final success-condition verification
- Bounded recovery for recognized transient conditions

Runtime outcomes are explicitly classified.

A successful execution returns:

```text
status = success
```

along with the capability's declared outputs.

A legitimate application outcome such as an unknown member returns:

```text
status = business_outcome
code = MEMBER_NOT_FOUND
```

This is intentionally distinguished from an automation failure.

The mock application also contains a transient-error scenario. Replay detects the known temporary condition, restores the workflow to a known entry state, and retries within a bounded retry budget.

An execution problem such as an unresolved target produces a structured hard failure:

```text
status = hard_failure
code = STEP_EXECUTION_FAILED
step = <failed step>
```

Replay stops rather than blindly continuing after losing confidence in the application state.

The implementation focuses primarily on runtime failures. UI drift is handled through semantic locators, fallback locators, and checkpoint validation.

# 4. Heterogeneity & multi-tenant

The primary abstraction for heterogeneous applications is `Surface`.

The discovery agent and replay engine operate on logical actions and targets rather than directly depending on Playwright APIs.

`PlaywrightSurface` currently translates those operations into browser interactions.

A future desktop implementation could expose the same logical interface while using Windows UI Automation, macOS Accessibility APIs, or another OS-level automation mechanism.

A more complex legacy web adapter could similarly handle frames, unusual DOM structures, accessibility information, and other application-specific details without changing the capability contract.

For multi-tenant deployment, I would separate reusable vendor-level capabilities from tenant-specific application profiles.

Conceptually:

```text
vendor capability
        ↓
application/version profile
        ↓
tenant-specific overrides
```

Organizations using the same underlying vendor application should generally share the same base capability.

Tenant profiles could contain only necessary differences such as:

- Route variations
- Branding-specific accessible names
- Feature flags
- Application versions
- Locator overrides

Before executing an artifact against another tenant, a production system should validate an application fingerprint using known routes, page landmarks, expected controls, and available version information.

If the target does not match an approved application variant, replay should stop or request review rather than assuming that an artifact recorded against another tenant is safe to execute.

I did not implement full multi-tenant infrastructure or desktop automation. Instead, the system boundaries were designed so those capabilities could be added without replacing the discovery/artifact/replay architecture.

# 5. Escalation & handoff

Human intervention is implemented as an explicit transfer of control over the existing live browser session.

When an action requires intervention, automation pauses without destroying or recreating the browser.

The handoff flow is:

```text
automation running
        ↓
intervention required
        ↓
automation pauses
        ↓
current state captured
        ↓
human uses same browser
        ↓
human interaction recorded
        ↓
human returns control
        ↓
checkpoint verified
        ↓
automation resumes
```

Preserving the same browser is important because it retains session state such as navigation, form values, cookies, and other application context.

The handoff implementation captures the current state, records basic human click/input evidence, and waits for the operator to signal that control should return to automation.

After control returns, replay verifies the expected checkpoint before continuing.

Handoff evidence is stored under `evidence/handoff/`.

The operator interface is intentionally minimal and terminal-driven. In a production system, I would expose the same control-transfer mechanism through an authenticated operator console with session assignment, ownership, timeouts, and explicit control leases.

The important architectural seam demonstrated here is that automation can pause, allow a person to control the same live application session, verify the resulting state, and safely resume.

# 6. Safety

A configurable `PolicyEngine` evaluates execution before actions are performed.

The current policy layer supports:

- Host allowlisting
- Permitted action types
- Conservative handling of potentially risky or irreversible actions

Normal lookup and read operations can execute automatically.

Actions associated with operations such as transfers, payments, transaction confirmation, or account closure are treated conservatively and routed to human intervention instead of being automatically executed.

For this small demonstration, risky actions are identified using a simple configurable classification mechanism. In a production system, I would encode risk classifications directly into reviewed capability metadata and organization-controlled policy configuration rather than depending on free-text step descriptions.

Sensitive-data handling is also conservative.

API credentials are provided through environment configuration and are not written into capability artifacts.

Invocation inputs written to structured evidence are redacted.

Discovery evidence avoids persisting complete page observations because those observations can contain member information or account values.

A production implementation should extend this with configurable field-level redaction, encryption, access controls, audit retention policies, and tenant-specific data-handling rules.

# 7. Cuts

I intentionally prioritized one complete end-to-end vertical slice over broad feature coverage.

The following were not implemented:

- Production multi-tenant infrastructure
- Desktop automation
- Distributed workers or queues
- Persistent capability database
- Polished operator console
- Production authentication and authorization
- Automatic cross-tenant capability canonicalization
- Open-ended LLM recovery during deterministic replay
- Advanced visual or screenshot-based targeting
- Production-grade secret management
- Comprehensive monitoring infrastructure

The current `ArtifactBuilder` is intentionally capability-specific: it parameterizes discovered values and preserves discovered locators, but capability metadata such as parameter names, extraction targets, checkpoints, and business outcomes are defined for the `get_savings_balance` flow. A production version would infer or configure these generically when promoting a discovery run into a reusable capability.

These cuts were deliberate because they are not necessary to demonstrate the central system design.

The implemented path covers:

```text
natural-language goal
        ↓
genuine LLM-driven UI discovery
        ↓
typed reusable capability artifact
        ↓
parameterized deterministic replay
        ↓
checkpoint verification
        ↓
structured output extraction
        ↓
business-outcome handling
        ↓
recoverable runtime handling
        ↓
hard-failure reporting
        ↓
policy enforcement
        ↓
live human handoff
        ↓
evidence capture
```

With additional time, I would prioritize artifact approval and lifecycle states, application fingerprints for safe cross-tenant reuse, stronger configurable redaction, explicit per-step retry policies, multi-run stability testing, and a production operator interface.