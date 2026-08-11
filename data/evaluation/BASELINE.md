# Evaluation Baseline

Current baseline was created from three consecutive
live evaluation runs using the local Ollama provider.

Baseline acceptance results:

- Hard pass rate: 100%
- Quality pass rate: 100%
- First-pass structured output rate: 100%
- Repair rate: 0%
- Critical case `model_location_mismatch`: 3/3 passed

The baseline represents the accepted quality level
before introducing the regression/release gate.

Latency is not currently used as a baseline acceptance
metric because local Ollama timing depends on warm-up
and machine load.