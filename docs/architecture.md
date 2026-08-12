# ML Incident Copilot Architecture

## Goal

ML Incident Copilot analyzes prediction requests and produces
structured incident reports.

The system deliberately separates deterministic facts from
LLM-generated explanation.

## Main flow

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
Issue codes + verified tool data
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
Python assembles IncidentFinding
        |
        v
IncidentReport



### Grounding boundary

#### Python owns factual fields:

issue code
evidence source
possible causes
recommended checks
verified numeric and categorical facts

#### The LLM owns only:

concise engineering explanation

The LLM does not decide which issue occurred.

### Structured output

LLM responses are validated with Pydantic.

Invalid structured output receives one repair attempt.

The run records:

provider
model
attempt count
analysis traces
### API

FastAPI exposes:

GET /v1/health
POST /v1/incidents/analyze
runtime feedback endpoint

API errors use a structured error contract and trace IDs.

### Runtime observability

Runtime analysis records are stored in JSONL.

Human feedback can be associated with a run through its trace ID.

run
 |
 +--> feedback
        |
        v
EvaluationCandidate
        |
        v
human review
        |
        v
evaluation case draft
### Evaluation

The evaluation harness supports:

deterministic evaluation
live LLM evaluation
hard correctness checks
explanation quality checks
structured-output first-pass tracking
repair tracking
token and timing metrics
### Release quality flow
pytest
  |
  v
live evaluation
  |
  v
baseline comparison
  |
  v
release policy
  |
  v
PASS / FAIL

The current accepted baseline tracks:

hard pass rate
quality pass rate
first-pass structured-output rate
repair rate
critical issue behavior

The complete local gate is:

python -m scripts.run_release_gate