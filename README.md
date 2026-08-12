# ML Incident Copilot

ML Incident Copilot is a small AI/ML engineering project for
investigating suspicious machine-learning predictions.

It combines deterministic domain checks with a local LLM to
produce structured, grounded incident reports.

The main design principle is simple:

> deterministic Python code establishes the facts;
> the LLM explains those facts.

The LLM does not decide which incident occurred and does not
construct factual report fields.

## What the project demonstrates

- Python-based agent orchestration
- deterministic domain tools
- local LLM integration through Ollama
- structured LLM output with Pydantic
- retry/repair handling
- evidence-grounded generation
- one-issue-per-LLM-call isolation
- FastAPI integration
- runtime tracing and feedback
- deterministic and live evaluation
- feedback-driven regression dataset growth
- evaluation baselines
- regression comparison
- release quality gates

## Architecture

```text
PredictionRequest
        |
        v
Deterministic tools
        |
        v
Issue codes + verified evidence
        |
        v
Grounded issue context
        |
        v
LLM explanation
        |
        v
Python-built IncidentReport


More detail is available in:

docs/architecture.md


## Why grounding matters

An earlier version passed broad tool output to the LLM.

For example, a model-location issue contained both:

request location: unknown_district
model location:   district_07
model version:    district_07_v3

A small local model could confuse the location and model-version
fields.

The current architecture reduces each issue to minimal verified
evidence plus a Python-generated grounded statement before the
LLM is called.

This produced stable results across repeated live evaluation runs.


## Quick start

Create and activate a virtual environment, then install the
project dependencies.

The project currently uses a local Ollama provider for live LLM
execution.

Make sure Ollama is running and the configured model is available.

Example:

ollama list

Run the portfolio demo:

python -m scripts.demo_portfolio


## API

Start the FastAPI application:

fastapi dev app/api.py

Interactive API documentation is then available through the
FastAPI development server.

Main endpoints:

GET  /v1/health
POST /v1/incidents/analyze

The API returns structured Pydantic responses and structured error
objects with trace IDs.


## Tests

Run the full unit/integration test suite:

python -m pytest -q


## Evaluation

Deterministic evaluation:

python -m scripts.run_evaluation --mode deterministic

Live evaluation using the configured LLM provider:

python -m scripts.run_evaluation --mode live

Evaluation reports are written under:

reports/evaluation/

The harness measures both deterministic correctness and LLM
behavior.

### Release gate

The project contains a local release-quality gate.

Run:

python -m scripts.run_release_gate

The command executes:

pytest
→ live evaluation
→ baseline comparison
→ release policy
→ PASS / FAIL

A successful release gate exits with status code 0.

A blocking regression exits with a non-zero status code.

### Feedback-driven evaluation growth

Runtime feedback is not automatically treated as ground truth.

Instead:

runtime run
→ human feedback
→ evaluation candidate
→ human review
→ case draft
→ reviewed evaluation case

This prevents noisy feedback from silently contaminating the
regression dataset.

### Project structure
app/
  agent.py
  api.py
  incident_builder.py
  report_validation.py
  schemas.py

  llm/
    base.py
    ollama_provider.py
    openai_provider.py
    repair.py

  tools/
    ...

  evaluation/
    ...

  observability/
    ...

data/
  evaluation/
  runtime/

scripts/
  demo_portfolio.py
  run_evaluation.py
  run_release_gate.py

tests/
  ...

docs/
  architecture.md

## Current limitations

This is a focused prototype rather than a production incident
management platform.

Current limitations include:

a small synthetic domain dataset
a small evaluation dataset
local JSONL runtime storage
a local Ollama-based live evaluation environment
manual human review before feedback becomes an evaluation case
no distributed persistence or production authentication
latency is observed but is not currently a blocking release
metric

These limitations are intentional for the current project stage.