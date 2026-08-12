# Publication Alignment Implementation Plan

> Goal: make the Nigeria-wide flooding–cholera platform scientifically honest, reproducible, testable, and aligned with a revised manuscript.

## Guardrails

- Preserve national scope: Nigeria's 36 states, FCT, and 774 LGAs.
- Cross River is a sentinel pilot only.
- Do not fabricate NCDC/SORMAS provenance, validation, p-values, lag results, or approvals.
- Distinguish current risk scoring from prediction/forecasting.
- Keep existing user changes intact; work on a dedicated branch after recording the dirty-tree baseline.

## Workstreams

1. **Reproducible evidence pipeline**
   - Add explicit data manifest/schema/provenance records.
   - Add national coverage and completeness audit scripts.
   - Add deterministic analysis entry point producing machine-readable outputs.
   - Add analysis metadata: n, missingness, lag definition, r, CI, nominal p, adjusted inference status.

2. **Statistical corrections**
   - Replace minimum-overlap correlation output that permits n=3 as a publishable result.
   - Require a configurable minimum sample size and return an explicit exploratory status.
   - Add confidence intervals and multiple-testing metadata.
   - Keep the implementation association-only unless a separately validated forecasting pipeline is built.

3. **Risk-engine honesty and validation hooks**
   - Rename/document the model as heuristic weighted MCDA.
   - Expose weight source/version and data timestamps.
   - Prevent current-case leakage from being described as prospective prediction.
   - Add validation report schema and temporal holdout hooks without claiming validation until executed.

4. **Satellite provenance**
   - Record sensor/product, acquisition window, processing parameters, cloud/mask rules, threshold, and retrieval status.
   - Make mock/fallback data impossible to confuse with real observations in API output.

5. **Claims and UI language**
   - Replace unsupported UI/README language: real-time, validated, predictive, statistically significant, PCA-calibrated, and live SORMAS.
   - Add visible evidence-status labels: observed, computed, exploratory, demo, unavailable.

6. **Manuscript revision**
   - Rewrite title, abstract, methods, results, discussion, limitations, and conclusion around demonstrated capabilities and auditable evidence.
   - Retain national system scope and Cross River sentinel framing.
   - Add tables for data provenance, coverage, model definition, and validation requirements.

7. **Verification**
   - Run backend tests, frontend tests, lint/type checks where available.
   - Run the evidence pipeline against available local assets.
   - Generate a code-paper reconciliation report and revised DOCX/PDF.
   - Review the final diff independently before commit.

## Acceptance criteria

- No unsupported quantitative claim remains in the revised manuscript.
- Every retained statistic has a reproducible input/output artifact or is explicitly labelled unavailable.
- Code and paper agree on algorithm, data provenance, geography, temporal resolution, and evidence status.
- National scope is preserved; Cross River is not presented as national validation.
- Tests and analysis commands are documented with actual outputs.
- Final artifacts include the audit, revised manuscript, change log, and reproducibility appendix.

## Execution order

1. Preserve baseline and create branch.
2. Add tests for evidence-status semantics and statistical output contract.
3. Implement minimum safe evidence pipeline and metadata.
4. Implement code/documentation language alignment.
5. Run real data audit and tests.
6. Rewrite manuscript from verified outputs only.
7. Render and inspect DOCX/PDF; run final verification.
8. Commit the complete aligned change set.
