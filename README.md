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
* one repair attempt for invalid structured output or failed evidence checks
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

This design keeps issue detection and factual report construction deterministic while still using the LLM where natural-language reasoning is useful. The final consistency check verifies issue codes, evidence references, causes, and checks. The sparse-data and above-range explanations also receive focused checks of required evidence and can be repaired once. These checks cannot prove that every LLM-written sentence is factually correct; live evaluation checks selected terms and forbidden claims in the eleven bundled cases.

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

### 3. Run a request without an LLM

The repository includes a sample request. This command runs all deterministic diagnostics and uses a repeatable explanation stub, so it works without Ollama or an API key:

```powershell
python -m scripts.analyze
```

To analyze your own request, copy and edit [`examples/prediction_request.json`](examples/prediction_request.json), then run:

```powershell
python -m scripts.analyze --input my_request.json --full
```

`--input -` reads one JSON object from standard input. The default output is the incident report; `--full` also shows the diagnostic steps and LLM trace. The accepted fields are visible in the example and at `/docs` when the API is running. Reference data currently covers `district_07` and `district_08`; an arbitrary real-world location will be flagged as unsupported.

[`examples/sparse_request.json`](examples/sparse_request.json) shows a second scenario: a prediction inside the regional price range but based on a sparse reference sample.

### 4. Configure Ollama for live explanations

The repository includes `.env.example`.

Copy it to `.env` and set `OLLAMA_MODEL` to an installed model name. The example selects `phi4-mini:latest`.

Make sure Ollama is running and the selected model is available:

```powershell
ollama list
```

Run the same request with the real local model:

```powershell
python -m scripts.analyze --mode live
```

The older fixed-input portfolio demo is also available:

```powershell
python -m scripts.demo_portfolio
```

The demo runs a fixed incident request through the full agent pipeline and prints a structured result.

## Docker

Start Docker Desktop and an Ollama server on the host. Ensure that the model named by `OLLAMA_MODEL` is installed. The API binds to `127.0.0.1:8001` on the host by default; set `API_PORT` before starting Compose to choose another port. If the container cannot reach Ollama on Windows, configure the **host Ollama process** to listen on `0.0.0.0:11434` and restart it. This server setting is separate from the project's `.env` client setting; Compose sends requests to `host.docker.internal:11434`.

```powershell
docker compose up --build --wait -d
curl.exe http://localhost:8001/v1/health
curl.exe -X POST http://localhost:8001/v1/incidents/analyze -H "Content-Type: application/json" --data-binary "@examples/prediction_request.json"
docker compose logs -f --tail=100 api
```

Open `http://localhost:8001/docs` for the interactive API. To run a request in the container without Ollama:

```powershell
docker compose run --rm api python -m scripts.analyze --mode deterministic
```

Runtime JSONL records use a Docker named volume. Stop the service with `docker compose down`. The Compose setup uses the host's Ollama installation; it does not download a model into the container.

The container writes application events to standard output, so `docker compose logs -f api` shows them without opening the runtime volume. Events include service startup, analysis start and completion (trace ID, request ID, issue codes, provider, model, LLM call count and duration), failures, rejected requests, and feedback. Routine event lines omit request bodies, model responses and feedback comments. Set `APP_LOG_LEVEL` to control verbosity. Docker rotates logs after 10 MB and retains three files. The `X-Trace-ID` response header connects an API result to its log entries and persisted JSONL record.

If a Windows antivirus product intercepts HTTPS, a Docker build may fail with `CERTIFICATE_VERIFY_FAILED` while installing Python packages. With Avast Web/Mail Shield, export its public root certificate from the Windows certificate store and pass it to BuildKit as a secret. The certificate is used during package installation and is not stored in the image:

```powershell
$ca = Get-ChildItem Cert:\CurrentUser\Root | Where-Object Subject -like '*Avast Web/Mail Shield Root*' | Select-Object -First 1
$caFile = Join-Path $env:TEMP 'ml-incident-copilot-build-ca.pem'
$base64 = [Convert]::ToBase64String($ca.Export([Security.Cryptography.X509Certificates.X509ContentType]::Cert), [Base64FormattingOptions]::InsertLineBreaks)
[IO.File]::WriteAllText($caFile, "-----BEGIN CERTIFICATE-----`n$base64`n-----END CERTIFICATE-----`n")
docker buildx build --secret "id=pip_ca,src=$caFile" -t ml_incident_copilot-api --load .
docker compose up --no-build --wait -d
```

## API

Start the FastAPI application:

```powershell
python -m uvicorn app.api:app --host 127.0.0.1 --port 8000
```

The main endpoints are:

```text
GET  /v1/health
POST /v1/incidents/analyze
POST /v1/incidents/{trace_id}/feedback
```

The API uses structured Pydantic response models, structured error responses, and trace IDs for runtime diagnostics.

The health endpoint confirms that the API process started; it does not probe Ollama. A request with detected issues exercises the provider and returns a structured `503` if it cannot be reached.

## LLM providers

The project contains a provider abstraction under `app/llm/`.

Implemented providers include:

* Ollama for local execution;
* OpenAI as an alternative provider.

Provider construction is centralized in `app/llm/factory.py`.

The agent itself depends on the provider interface rather than a concrete vendor implementation.

Here “agent” means a fixed, testable Python orchestration policy. The repository does not call a Codex agent or the Codex CLI. The OpenAI provider uses the OpenAI Responses API, which is a separate optional integration and has not been verified with a paid live request.

## Tests

Run the full test suite:

```powershell
python -m pytest -q
```

The tests cover agent behavior, deterministic tools, incident assembly, grounding, API behavior, Ollama provider handling with fake clients, observability, evaluation candidates, baselines, regression comparison, release policy, and the release-gate runner. They do not require a running LLM or Docker. Use `--mode live` for a real Ollama run.

The OpenAI provider has contract tests with a fake SDK client; a real OpenAI request and a Codex agent invocation are outside the automated suite.

| Test group | What it checks |
| --- | --- |
| Domain tools and agent | Input consistency, model routing, reference-range checks, skipped steps, per-issue calls, repair and report assembly |
| API and runtime | HTTP contracts, error codes, trace IDs, JSONL records and feedback |
| LLM providers | Ollama schema handling and OpenAI structured-call contract with fake clients |
| Evaluation | Eleven bundled cases, candidate review/export, baseline comparison and release policy |

GitHub Actions runs the offline suite on Python 3.12 and 3.14 and builds a Docker image. CI does not need an Ollama server or an OpenAI key.

## Evaluation

The evaluation harness has two modes.

### Deterministic evaluation

```powershell
python -m scripts.run_evaluation --mode deterministic
```

This mode uses deterministic/fake LLM behavior and is useful for fast correctness checks.
It does not score natural-language explanation quality; its quality pass rate is `n/a`.

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

The baseline records the exact evaluation case IDs. A changed dataset blocks the release gate until a new baseline is accepted from three fully passing live runs with `scripts.create_evaluation_baseline --reports <first> <second> <third>`.

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

The local release gate combines the main quality checks into one command. It needs a working live Ollama provider:

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
  analyze.py

tests/
  ...

docs/
  architecture.md

examples/
  prediction_request.json
  sparse_request.json

Dockerfile
compose.yaml
```

Generated runtime and evaluation artifacts are kept separate from the core source code and are not intended to be committed as project source.

## Current limitations

This is a focused engineering prototype rather than a production incident-management platform.

Current limitations include:

* a small synthetic domain dataset;
* a small evaluation dataset (eleven synthetic cases);
* local JSONL runtime persistence;
* local Ollama-based live evaluation;
* manual human review before feedback becomes an evaluation case;
* no distributed persistence;
* no production authentication/authorization layer;
* no external queue or worker architecture;
* latency is observed but is not currently a blocking release metric;
* free-text explanations are constrained by prompts and sampled quality checks, not fully verified by deterministic grounding.

These constraints are intentional for the current project stage. The project focuses on reliable orchestration, grounding, evaluation, observability, and release-quality mechanics rather than infrastructure scale.
