# ML Incident Copilot

ML Incident Copilot is a compact AI/ML engineering project for investigating suspicious machine-learning predictions.

It combines deterministic domain checks with an LLM to produce structured, evidence-grounded incident reports. The project is intentionally designed so that the LLM does not decide what happened. Python code establishes the facts, and the LLM explains those facts in concise engineering language.

> **Design principle:** deterministic code owns the facts; the LLM owns only the explanation.

## What the project demonstrates

* Python-based agent orchestration
* deterministic validation and diagnostic tools
* local LLM integration with Ollama
* optional OpenAI provider support
* structured LLM output validated with Pydantic
* one repair attempt for invalid structured output
* evidence-grounded generation
* one issue per LLM call
* Python-side assembly of the final incident report
* FastAPI integration
* structured API errors and trace IDs
* runtime observability and human feedback
* deterministic and live evaluation modes
* feedback-driven evaluation dataset growth
* accepted evaluation baselines
* regression comparison
* release policy and an automated local release gate

## Architecture

```text
PredictionRequest
        |
        v
Deterministic tools
        |
        +-- validate_input
        +-- get_model_metadata
        +-- analyze_prediction
        +-- search_known_issues
        |
        v
Issue codes + verified evidence
        |
        v
Incident Builder
        |
        +-- relevant_evidence
        +-- grounded_statement
        |
        v
One issue = one LLM call
        |
        v
IssueAnalysis
(explanation only)
        |
        v
Python assembles IncidentFinding objects
        |
        v
Grounding / consistency validation
        |
        v
IncidentReport
```

A more detailed description is available in [`docs/architecture.md`](docs/architecture.md).

## Why grounding matters

An earlier design passed broad tool output to the LLM. That gave a small local model too much nearby information and made it easier to confuse related fields.

For example, a model-location issue could contain:

```text
request location: unknown_district
model location:   district_07
model version:    district_07_v3
```

The current architecture reduces every detected issue to:

* the issue code;
* the minimal verified evidence relevant to that issue;
* a Python-generated grounded statement.

The LLM receives this reduced context and returns only an `explanation`.

This design keeps issue detection and factual report construction deterministic while still using the LLM where natural-language reasoning is useful.

## Main execution flow

For every `PredictionRequest`, the agent:

1. validates the input;
2. checks model metadata and routing;
3. compares the prediction with regional reference data when available;
4. searches known issues for matching issue codes;
5. builds deterministic issue contexts;
6. calls the LLM once for each issue;
7. assembles the final report in Python;
8. validates the report against the observed evidence.

If no issue is detected, the report is completed without LLM-authored incident findings.

## Quick start

### 1. Create a virtual environment

```powershell
python -m venv .venv
```

Activate it on Windows:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 2. Install dependencies

For runtime use:

```powershell
python -m pip install -r requirements.txt
```

For development and testing:

```powershell
python -m pip install -r requirements-dev.txt
```

### 3. Configure the project

The repository includes `.env.example`.

Copy it to `.env` and adjust the provider/model configuration for your environment.

### 4. Prepare Ollama for local live runs

Make sure Ollama is running and the configured model is available:

```powershell
ollama list
```

The current local development setup uses `phi4-mini:latest`.

### 5. Run the portfolio demo

```powershell
python -m scripts.demo_portfolio
```

The demo runs a realistic incident request through the full agent pipeline and prints a structured result.

## API

Start the FastAPI application:

```powershell
fastapi dev app/api.py
```

The main endpoints are:

```text
GET  /v1/health
POST /v1/incidents/analyze
POST /v1/incidents/{trace_id}/feedback
```

The API uses structured Pydantic response models, structured error responses, and trace IDs for runtime diagnostics.

## LLM providers

The project contains a provider abstraction under `app/llm/`.

Implemented providers include:

* Ollama for local execution;
* OpenAI as an alternative provider.

Provider construction is centralized in `app/llm/factory.py`.

The agent itself depends on the provider interface rather than a concrete vendor implementation.

## Tests

Run the full test suite:

```powershell
python -m pytest -q
```

The tests cover agent behavior, deterministic tools, incident assembly, grounding, API behavior, Ollama provider handling, observability, evaluation candidates, baselines, regression comparison, release policy, and the unified release-gate runner.

## Evaluation

The evaluation harness has two modes.

### Deterministic evaluation

```powershell
python -m scripts.run_evaluation --mode deterministic
```

This mode uses deterministic/fake LLM behavior and is useful for fast correctness checks.

### Live evaluation

```powershell
python -m scripts.run_evaluation --mode live
```

This mode executes the configured real LLM provider.

Evaluation output is written under:

```text
reports/evaluation/<timestamp>/
```

A run can include:

```text
summary.json
report.md
cases.csv
baseline_comparison.json
release_gate_result.json
```

depending on which evaluation/release commands were executed.

### What the harness measures

The evaluation system tracks:

* hard correctness checks;
* explanation quality checks;
* first-pass structured-output success;
* repair usage;
* timing metrics;
* token metrics when available;
* behavior of explicitly critical cases.

## Evaluation baseline

The accepted baseline is stored in:

```text
data/evaluation/baseline.json
```

Its provenance is documented in:

```text
data/evaluation/BASELINE.md
```

The baseline records accepted behavior for metrics such as:

* hard pass rate;
* quality pass rate;
* first-pass rate;
* repair rate;
* critical-case pass rates.

A current evaluation can be compared with the baseline:

```powershell
python -m scripts.compare_evaluation_with_baseline --report <path-to-summary.json>
```

The comparison classifies tracked metrics as:

```text
SAME
IMPROVED
REGRESSED
NOT_COMPARED
```

## Release gate

The local release gate combines the main quality checks into one command:

```powershell
python -m scripts.run_release_gate
```

It runs:

```text
pytest
   |
   v
fresh live evaluation
   |
   v
baseline comparison
   |
   v
release policy
   |
   v
PASS / FAIL
```

The release policy is stored in:

```text
data/evaluation/release_policy.json
```

Blocking regressions produce `FAIL`. Non-blocking regressions can produce warnings.

A successful gate returns exit code `0`; a blocking failure returns a non-zero exit code.

## Runtime observability and feedback

Runtime analysis records are stored in JSONL and linked by trace IDs.

The observability layer records information such as:

* request and trace identifiers;
* outcome;
* provider/model information;
* prompt version;
* duration;
* agent result and analysis traces;
* error metadata when a run fails.

Human feedback can then be attached to a recorded run.

Feedback is intentionally **not** treated as automatic ground truth.

Instead, the project uses this review flow:

```text
runtime run
    |
    v
human feedback
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
     evaluation case draft
          |
          v
     reviewed cases.json update
```

This keeps runtime feedback useful without silently contaminating the regression dataset.

## Project structure

```text
app/
  agent.py
  api.py
  api_models.py
  bootstrap.py
  config.py
  incident_builder.py
  issue_analysis_prompts.py
  report_validation.py
  schemas.py

  evaluation/
    baseline_comparison.py
    baseline_schemas.py
    baseline_store.py
    candidate_builder.py
    candidate_export.py
    candidate_schemas.py
    candidate_store.py
    comparison_schemas.py
    dataset.py
    fake_provider.py
    release_gate.py
    release_gate_schemas.py
    release_gate_store.py
    report.py
    runner.py
    schemas.py
    summary_reader.py

  llm/
    base.py
    factory.py
    ollama_provider.py
    openai_provider.py
    repair.py

  observability/
    bootstrap.py
    records.py
    schemas.py
    store.py

  tools/
    input_validator.py
    issue_search.py
    model_registry.py
    prediction_analyzer.py
    runner.py

data/
  known_issues.json
  location_stats.json
  model_registry.json

  evaluation/
    baseline.json
    BASELINE.md
    cases.json
    release_policy.json

  runtime/
    runs.jsonl

scripts/
  build_evaluation_candidates.py
  compare_evaluation_with_baseline.py
  create_evaluation_baseline.py
  demo_agent.py
  demo_llm_provider.py
  demo_portfolio.py
  export_approved_candidates.py
  run_evaluation.py
  run_release_gate.py

tests/
  ...

docs/
  architecture.md
```

Generated runtime and evaluation artifacts are kept separate from the core source code and are not intended to be committed as project source.

## Current limitations

This is a focused engineering prototype rather than a production incident-management platform.

Current limitations include:

* a small synthetic domain dataset;
* a small evaluation dataset;
* local JSONL runtime persistence;
* local Ollama-based live evaluation;
* manual human review before feedback becomes an evaluation case;
* no distributed persistence;
* no production authentication/authorization layer;
* no external queue or worker architecture;
* latency is observed but is not currently a blocking release metric.

These constraints are intentional for the current project stage. The project focuses on reliable orchestration, grounding, evaluation, observability, and release-quality mechanics rather than infrastructure scale.
