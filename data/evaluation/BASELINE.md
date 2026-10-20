# Accepted evaluation baseline

The baseline in `baseline.json` was regenerated on 2026-10-20 after expanding
the synthetic evaluation dataset from six to eleven cases. It records the exact
eleven case IDs, so a release gate cannot compare rates against a different
dataset without failing.

Three consecutive live Ollama runs were accepted:

| Local report directory | Cases | Hard | Explanation quality | First pass | Repairs |
| --- | ---: | ---: | ---: | ---: | ---: |
| `20261020_120849` | 11 | 100% | 100% | 100% | 0 |
| `20261020_121022` | 11 | 100% | 100% | 100% | 0 |
| `20261020_121249` | 11 | 100% | 100% | 100% | 0 |

The critical `model_location_mismatch` case passed in all three runs. Local
reports are generated under `reports/evaluation/` and are excluded from Git.
The baseline can be recreated from three live `summary.json` files with:

```powershell
python -m scripts.create_evaluation_baseline --reports <first-summary> <second-summary> <third-summary>
```

The command validates all three summaries before writing the accepted baseline.
Latency is excluded because local Ollama timing depends on warm-up and machine
load. This baseline is a quality threshold for a small synthetic dataset, not a
production accuracy estimate.
