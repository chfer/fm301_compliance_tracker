## Plan: Add Compliance Tracking Summaries

Add a summary layer after validation. It will parse every `*.results.json`, calculate mandatory-only scores for the five requested category families, write a sibling `*.results.summary.json`, then create `data/validation/<converter>/<converter>-compliance.json`.

**Steps**
1. Add `summaries.py` to parse and validate checker rows: category index `0`, applicability index `7`, result index `8`.
2. Normalize attribute categories at the first `:`. For example, `sweep_variables:sweep_0/time` contributes to `sweep_variables`.
3. Include only `Global_Attributes`, `Global_Ancillary_variables`, `sweep_variables`, `radar_parameters`, and `radar_calibration`, and only rows marked `Mandatory`.
4. Per file, write counts for passed, failed, and total mandatory checks plus percentage per eligible category. Omit categories with no mandatory items.
5. Calculate each file’s overall score by pooling all eligible mandatory checks:
   $100 \times \frac{\text{mandatory passes}}{\text{mandatory total}}$.
6. Aggregate the raw counts from all per-file summaries for each converter. Do not average already rounded percentages.
7. Integrate summary creation after successful validation. Malformed/missing result files become logged failed summary outcomes but do not stop other files.
8. Prevent stale summaries from a previous run being counted after a failed validation.
9. Add unit and workflow tests for normalization, filtering, score arithmetic, malformed input, multi-file converter aggregation, and output paths.
10. Update the README with artifact names and scoring rules.

**JSON Contents**
Each file summary will contain:
- Source result file
- `categories`: per-category counts and percentage
- `overall`: pooled counts and percentage

Each converter summary will contain:
- Converter name
- Included file summaries
- Per-category pooled counts and percentages
- Overall pooled score

**Decisions**
- Optional and `data_variables` rows do not contribute.
- Categories without mandatory rows are omitted.
- All mandatory checks have equal weight, both within and across files.
- Invalid JSON/rows are excluded, logged, and result in a nonzero tracker exit after remaining work completes.
- This phase produces JSON summaries only; charts and historical trend comparisons are outside scope.
