# ML Incident Copilot Architecture

## 1. Goal

ML Incident Copilot analyzes machine-learning prediction requests and produces structured incident reports for suspicious or inconsistent predictions.

The architecture deliberately separates deterministic facts from LLM-generated language.

The core rule is:

> **Python determines what happened. The LLM explains why the detected issue matters.**

The LLM does not decide which issue occurred and does not own factual fields in the final report.

## 2. High-level architecture

```text
PredictionRequest
        |
        v
+-----------------------------+
| Deterministic diagnostics   |
|-----------------------------|
| validate_input              |
| get_model_metadata          |
| analyze_prediction          |
| search_known_issues         |
+-----------------------------+
        |
        v
Issue codes + verified tool data
        |
        v
+-----------------------------+
| Incident Builder            |
|-----------------------------|
| relevant_evidence           |
| grounded_statement          |
| possible_causes             |
| recommended_checks          |
+-----------------------------+
        |
        v
One IssueContext per issue
        |
        v
+-----------------------------+
| LLM                         |
|-----------------------------|
| one issue per call          |
| returns explanation only    |
| structured with Pydantic    |
| max one repair attempt      |
+-----------------------------+
        |
        v
IssueAnalysis
        |
        v
+-----------------------------+
| Python report assembly      |
|-----------------------------|
| IncidentFinding             |
| IncidentReport              |
+-----------------------------+
        |
        v
Grounding / consistency validation
        |
        v
AgentRun
```

## 3. Main components

### 3.1 Agent orchestration

`app/agent.py` owns the execution policy.

For each request it:

1. executes the required deterministic tools;
2. accumulates detected issue codes;
3. skips checks that are not meaningful for the current request;
4. builds one deterministic `IssueContext` per detected issue;
5. calls the LLM once per issue;
6. assembles the final report in Python;
7. performs a final consistency check;
8. returns an `AgentRun` with steps, report, and analysis traces.

This is a policy-based agent rather than an unconstrained autonomous agent. The execution order is explicit and testable.

### 3.2 Deterministic tools

The deterministic tool layer lives under `app/tools/`.

```text
input_validator.py
model_registry.py
prediction_analyzer.py
issue_search.py
```

The current flow uses four logical checks.

#### `validate_input`

Checks request-level consistency and supported locations.

Examples of issue codes include:

* `unsupported_location`
* `road_access_conflict`

#### `get_model_metadata`

Checks whether the requested model version exists, is active, and is appropriate for the request.

Examples include:

* `unknown_model_version`
* `inactive_model_version`
* `model_location_mismatch`
* `area_outside_model_range`

#### `analyze_prediction`

Compares the prediction with regional reference statistics when the request location is supported.

Example:

* `prediction_below_reference_range`

#### `search_known_issues`

Maps observed issue codes to configured known issues and returns deterministic hypotheses/checks that may be included in the final report.

## 4. Grounding boundary

The grounding boundary is the most important architectural constraint in the project.

### Python owns factual fields

Python owns:

* issue codes;
* evidence source/tool;
* verified numeric and categorical facts;
* possible causes from configured known issues;
* recommended checks from configured known issues;
* final report structure;
* request/report consistency.

### The LLM owns only

The LLM owns:

* a concise engineering `explanation`.

The LLM is not asked to:

* invent an issue code;
* choose an evidence source;
* create possible causes;
* create recommended checks;
* decide report status;
* assemble the final `IncidentReport`.

This sharply reduces the surface available for hallucination.

## 5. Issue context reduction

Broad tool output is not sent directly to the LLM.

For each detected issue, `incident_builder.py` creates an issue-specific context containing only the information needed for that issue.

Conceptually:

```text
full request + all tool output
        |
        v
deterministic issue extraction
        |
        v
IssueContext
  - issue_code
  - evidence_tool
  - relevant_evidence
  - grounded_statement
  - possible_causes
  - recommended_checks
        |
        v
minimal LLM prompt
```

The prompt itself focuses on:

* issue code;
* relevant verified evidence;
* Python-generated grounded statement.

This keeps unrelated fields out of the model context.

## 6. One issue per LLM call

Each issue is analyzed independently.

```text
issue A -> LLM call A -> explanation A
issue B -> LLM call B -> explanation B
issue C -> LLM call C -> explanation C
```

This design has several benefits:

* smaller prompts;
* less cross-issue contamination;
* easier tracing;
* easier evaluation;
* easier repair;
* clearer attribution when one issue fails.

The output model is `IssueAnalysis`, which contains only the explanation field.

## 7. Structured output and repair

LLM responses are validated with Pydantic.

The structured-output flow is:

```text
LLM response
    |
    v
Pydantic validation
    |
    +-- valid -> continue
    |
    `-- invalid
          |
          v
      one repair attempt
          |
          +-- valid -> continue
          |
          `-- invalid -> error
```

The project intentionally limits repair instead of retrying indefinitely.

The resulting trace records the number of attempts so evaluation can distinguish:

* first-pass success;
* successful repair;
* repair exhaustion.

## 8. Final report assembly

The final `IncidentReport` is assembled in Python.

For each issue, Python combines:

```text
deterministic IssueContext
        +
LLM explanation
        |
        v
IncidentFinding
```

The report therefore contains deterministic factual fields plus a model-generated explanation, rather than allowing the model to construct the entire report.

A final grounding/consistency validation step verifies that the assembled report still matches the issues and tool evidence observed during the run.

## 9. LLM provider abstraction

The LLM layer is isolated under `app/llm/`.

```text
base.py
factory.py
ollama_provider.py
openai_provider.py
repair.py
```

`base.py` defines the provider contract.

`factory.py` selects the configured provider.

The current implementation supports:

* Ollama for local execution;
* OpenAI as an alternative provider.

The agent depends on the provider interface, not directly on a specific SDK.

This makes model/provider changes local to the LLM layer.

## 10. API layer

FastAPI exposes the agent through `app/api.py`.

Main endpoints:

```text
GET  /v1/health
POST /v1/incidents/analyze
POST /v1/incidents/{trace_id}/feedback
```

The API layer provides:

* Pydantic request/response contracts;
* trace IDs;
* structured error responses;
* mapping of LLM/provider failures to API errors;
* runtime recording of successful and failed analysis runs;
* feedback submission linked to an existing trace.

The domain agent is kept separate from FastAPI so it can be tested without HTTP.

## 11. Runtime observability

Observability code lives under `app/observability/`.

```text
bootstrap.py
records.py
schemas.py
store.py
```

Runtime records are stored in JSONL.

A run record can include:

* trace ID;
* request ID;
* timestamp;
* duration;
* outcome;
* request payload;
* agent result;
* prompt version;
* provider/model names;
* error metadata.

This allows a production-like run to be inspected after the request has completed.

## 12. Feedback-driven evaluation growth

Human feedback is linked to runtime runs through trace IDs.

The project deliberately avoids turning all feedback directly into evaluation ground truth.

The flow is:

```text
IncidentRunRecord
        |
        v
IncidentFeedbackRecord
        |
        v
candidate_builder
        |
        v
EvaluationCandidate
        |
        v
human review
        |
        +-- rejected
        |
        `-- approved
              |
              v
         case draft export
              |
              v
         reviewed update of cases.json
```

Candidate creation is idempotent and uses feedback identity to avoid duplicate candidates.

This creates a controlled bridge from runtime failures to regression tests.

## 13. Evaluation architecture

Evaluation code lives under `app/evaluation/`.

The harness supports two modes.

### Deterministic mode

Uses deterministic/fake LLM behavior.

Purpose:

* fast repeatable correctness checks;
* tool and orchestration validation;
* regression testing without model variability.

### Live mode

Uses the configured real LLM provider.

Purpose:

* explanation-quality checks;
* structured-output behavior;
* repair behavior;
* model/provider regression detection.

### Evaluation metrics

The harness tracks:

* hard pass rate;
* quality pass rate;
* first-pass structured-output rate;
* repair usage/rate;
* timing metrics;
* token metrics when available;
* critical-case behavior.

Evaluation reports are written under:

```text
reports/evaluation/<timestamp>/
```

Typical artifacts include:

```text
summary.json
report.md
cases.csv
```

## 14. Baseline and regression comparison

An accepted evaluation baseline is stored in:

```text
data/evaluation/baseline.json
```

Its provenance is documented in:

```text
data/evaluation/BASELINE.md
```

A new evaluation summary is normalized and compared with the baseline.

For each tracked metric, the comparison produces one of:

```text
same
improved
regressed
not_compared
```

The comparison is saved as:

```text
baseline_comparison.json
```

Important detail: the comparison layer describes **what changed**. It does not decide whether the change is acceptable.

## 15. Release policy

Release acceptance rules are stored separately in:

```text
data/evaluation/release_policy.json
```

The policy decides which comparison results are blocking.

The current policy conceptually treats:

```text
hard correctness regression     -> blocking
quality regression              -> blocking
critical-case regression        -> blocking
missing blocking metric         -> blocking
wrong evaluation mode           -> blocking

first-pass regression           -> warning
repair-rate regression          -> warning
```

This separation keeps measurement and policy independent:

```text
baseline comparison
    = what changed?

release policy
    = is that change acceptable?
```

## 16. Unified local release gate

The complete release-quality flow is exposed through:

```powershell
python -m scripts.run_release_gate
```

The runner executes:

```text
pytest
  |
  +-- FAIL -> stop, exit 1
  |
  v
fresh live evaluation
  |
  v
find newly created summary.json
  |
  v
baseline comparison
  |
  v
release policy
  |
  v
release_gate_result.json
  |
  +-- PASS -> exit 0
  |
  `-- FAIL -> exit 1
```

For a complete run, the report directory can contain:

```text
summary.json
report.md
cases.csv
baseline_comparison.json
release_gate_result.json
```

The non-zero failure exit code makes the local release gate suitable for future CI integration.

## 17. Data layout

The project keeps static domain data, evaluation data, and runtime data separate.

```text
data/
  known_issues.json
  location_stats.json
  model_registry.json

  evaluation/
    cases.json
    baseline.json
    BASELINE.md
    release_policy.json
    case_drafts.json

  runtime/
    runs.jsonl
```

Generated runtime/evaluation artifacts are not source-of-truth configuration and are kept separate from versioned evaluation inputs.

## 18. Key design decisions

### Deterministic-first diagnostics

Issue detection is deterministic because these decisions should be reproducible and testable.

### LLM only for language generation

The LLM is used where free-form language adds value, not where deterministic code is safer.

### Minimal per-issue context

Reducing context lowers the chance that the model combines unrelated evidence.

### Human review before dataset promotion

Runtime feedback can be noisy or incomplete, so it is not automatically promoted to regression ground truth.

### Separate baseline from release policy

The baseline captures accepted behavior. The policy defines what degradation is allowed.

### Local quality gate before CI

The project first makes the release check deterministic and scriptable locally, including machine-readable exit codes, before adding external CI infrastructure.

## 19. Current limitations

The current architecture is deliberately small and local.

It does not currently include:

* distributed persistence;
* production authentication/authorization;
* external job queues/workers;
* distributed tracing infrastructure;
* a large production evaluation dataset;
* automatic promotion of human feedback to ground truth;
* latency as a blocking release criterion.

These limits are intentional. The current focus is on safe LLM boundaries, reproducible evaluation, controlled feedback ingestion, and release-quality checks.
